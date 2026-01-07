#openbot\features\downloader\mt_downloader.py
import logging
import os
import time
import asyncio
import re
import sqlite3
import traceback
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from core.command_registry import register_handler
from telethon import types

logger = logging.getLogger(__name__)

__MODULE_NAME__ = "MTProto手动秒下引擎"

# ===================== 0. 基础配置与数据库 =====================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "download")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
DB_PATH = os.path.join(DOWNLOAD_DIR, "download_tasks.db")

batch_controls = {}
task_semaphore = asyncio.Semaphore(10)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS dl_tasks 
                    (jid INTEGER, msg_id INTEGER, chat_id INTEGER, chat_name TEXT, tag TEXT, status INTEGER)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS active_jobs 
                    (jid PRIMARY KEY, link TEXT, tag TEXT, is_monitor INTEGER, user_chat_id INTEGER)''')
    conn.commit()
    conn.close()

def get_next_jid():
    try:
        conn = sqlite3.connect(DB_PATH)
        res = conn.execute("SELECT MAX(jid) FROM active_jobs").fetchone()
        conn.close()
        return (res[0] + 1) if res and res[0] else 1
    except: return 1

def save_active_job(jid, link, tag, is_monitor, user_chat_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR REPLACE INTO active_jobs VALUES (?, ?, ?, ?, ?)", 
                 (jid, link, tag, 1 if is_monitor else 0, user_chat_id))
    conn.commit(); conn.close()

def remove_active_job(jid):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM active_jobs WHERE jid = ?", (jid,))
    conn.commit(); conn.close()

def save_task(jid, msg_id, chat_id, chat_name, tag):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR IGNORE INTO dl_tasks VALUES (?, ?, ?, ?, ?, 0)", (jid, msg_id, chat_id, chat_name, tag))
    conn.commit(); conn.close()

def mark_done(jid, msg_id, chat_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE dl_tasks SET status = 1 WHERE jid = ? AND msg_id = ? AND chat_id = ?", (jid, msg_id, chat_id))
    conn.commit(); conn.close()

# ===================== 1. UI 滚动看板 =====================
class IndependentUI:
    def __init__(self, bot, chat_id, title="进度"):
        self.bot = bot
        self.chat_id = chat_id
        self.title = title
        self.tasks = {}
        self.task_order = []
        self.status_msg = None
        self.lock = asyncio.Lock()
        self.last_update = 0
        self.monitor_stats = {"total": 0, "done": 0}

    async def update(self, tid, icon, detail, force=False):
        if tid not in self.tasks: self.task_order.append(tid)
        self.tasks[tid] = f"{icon} <code>#{tid}</code>|{detail}"
        now = time.time()
        if not force and (now - self.last_update < 4.0): return

        async with self.lock:
            self.last_update = time.time()
            header = f"📦 <b>{self.title}</b>\n━━━━━━━━━━━━━━━\n"
            stats = f"⏳ 状态: {self.monitor_stats['done']} / {self.monitor_stats['total']} 完成\n━━━━━━━━━━━━━━━\n"
            lines = [self.tasks[id] for id in self.task_order[-15:]]
            text = header + stats + "\n".join(lines)
            try:
                if self.status_msg: await self.status_msg.edit_text(text, parse_mode="HTML")
                else: self.status_msg = await self.bot.send_message(self.chat_id, text, parse_mode="HTML")
            except: pass

# ===================== 2. 核心下载原子操作 (已修改路径样式) =====================
async def _core_download_engine(client, jid, msg_id, chat_id, chat_name, ui, task_key):
    async def cb(c, t):
        if task_key not in batch_controls or batch_controls[task_key]["cancel"]: raise Exception("STOP")
        await batch_controls[task_key]["event"].wait()
        await ui.update(msg_id, "🔵", f"{c/1024**2:.1f}MB", force=False)
    
    try:
        m = await client.get_messages(chat_id, ids=msg_id)
        if not m or not m.media: return
        
        # 💡 修改点 1：使用原始 ID，不删 -100
        source_id = str(chat_id)
        
        # 💡 修改点 2：构造精准路径：download/{source_id}/{chat_name} (移除 video/photo 层级)
        safe_chat_name = re.sub(r'[\\/:*?"<>|]', '_', chat_name)
        save_dir = os.path.join(DOWNLOAD_DIR, source_id, safe_chat_name)
        os.makedirs(save_dir, exist_ok=True)
        
        # 💡 修改点 3：增强的文件名救助逻辑
        fname = f"{msg_id}"
        if hasattr(m.media, 'document'):
            for attr in m.media.document.attributes:
                if isinstance(attr, types.DocumentAttributeFilename): fname = attr.file_name
        
        # 自动补全后缀
        if "." not in fname:
            is_video = "video" in str(getattr(m.media, 'document', ''))
            fname += ".mp4" if is_video else ".jpg"
        
        fpath = os.path.join(save_dir, fname)
        
        # 💡 修改点 4：去重逻辑
        if os.path.exists(fpath):
            mark_done(jid, msg_id, chat_id)
            ui.monitor_stats["done"] += 1
            await ui.update(msg_id, "🟢", "已存在", force=True)
            return

        await ui.update(msg_id, "🟡", "下载中", force=False)
        # 💡 修改点 5：原子化保存 (.temp)
        await client.download_media(m, file=fpath + ".temp", progress_callback=cb)
        if os.path.exists(fpath + ".temp"):
            os.rename(fpath + ".temp", fpath)
            mark_done(jid, msg_id, chat_id)
            ui.monitor_stats["done"] += 1
            await ui.update(msg_id, "✅", "完成", force=True)
            
    except Exception as e:
        if "STOP" not in str(e): 
            logger.error(f"下载异常 #{msg_id}: {e}")
            await ui.update(msg_id, "🔴", "失败", force=True)

# ===================== 3. 搜刮引擎 =====================
async def _scrape_and_run(client, bot, user_chat_id, chat_key, sub, is_monitor, jid, task_key):
    try:
        while True:
            if task_key not in batch_controls or batch_controls[task_key]["cancel"]: break
            try: ent = await client.get_entity(chat_key)
            except Exception as e:
                await bot.send_message(user_chat_id, f"❌ 任务 #{jid} 失败: {e}"); break

            if not batch_controls[task_key].get("ui"):
                ui_title = f"{'监控' if is_monitor else '下载'} #{jid} | {ent.title}"
                batch_controls[task_key]["ui"] = IndependentUI(bot, user_chat_id, ui_title)
            
            ui = batch_controls[task_key]["ui"]
            all_ids, processed_groups = [], set()
            search_term = None if sub == "all" else sub

            async for m in client.iter_messages(ent, search=search_term):
                if task_key not in batch_controls or batch_controls[task_key]["cancel"]: return
                if not m.media: continue
                if m.grouped_id:
                    if m.grouped_id in processed_groups: continue
                    processed_groups.add(m.grouped_id)
                    async for gm in client.iter_messages(ent, min_id=m.id-10, max_id=m.id+10):
                        if gm.grouped_id == m.grouped_id and gm.media:
                            all_ids.append(gm.id); save_task(jid, gm.id, ent.id, ent.title, sub)
                            await ui.update(gm.id, "🔍", "发现")
                else:
                    all_ids.append(m.id); save_task(jid, m.id, ent.id, ent.title, sub)
                    await ui.update(m.id, "🔍", "发现")
                ui.monitor_stats["total"] = len(all_ids)

            if all_ids:
                await bot.send_message(user_chat_id, f"📦 任务 #{jid} 搜刮完毕，开始下载...")
                for i in range(0, len(all_ids), 5):
                    if task_key not in batch_controls or batch_controls[task_key]["cancel"]: break
                    await batch_controls[task_key]["event"].wait()
                    async with task_semaphore:
                        tasks = [_core_download_engine(client, jid, mid, ent.id, ent.title, ui, task_key) for mid in all_ids[i:i+5]]
                        await asyncio.gather(*tasks)
            if not is_monitor: break
            await asyncio.sleep(3600)
    except: logger.error(traceback.format_exc())
    finally:
        if not is_monitor: remove_active_job(jid); batch_controls.pop(task_key, None)

# ===================== 4. 指令处理器 =====================
def parse_link(link):
    if "/+" in link or "joinchat" in link: return link
    parts = link.rstrip('/').split('/')
    if 't.me/c/' in link:
        for p in parts:
            if p.isdigit() and len(p) > 5: return int("-100" + p)
    return parts[-1]

async def handle_dl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    manager = getattr(handle_dl_command, "manager", None) or context.bot_data.get('manager')
    if not manager or not manager.mtproto_client: return await update.message.reply_text("❌ MTProto 未就绪")
    msg = update.effective_message
    if not context.args: return await msg.reply_text("💡 用法: /dl [链接] [关键字/all]")
    
    jid = get_next_jid(); task_key = f"{msg.chat_id}_{jid}"
    is_monitor = "/dl_all" in msg.text
    link, sub = context.args[0].strip(), (context.args[1] if len(context.args) > 1 else "all")
    
    save_active_job(jid, link, sub, is_monitor, msg.chat_id)
    batch_controls[task_key] = {"event": asyncio.Event(), "cancel": False, "tag": sub, "jid": jid, "ui": None}
    batch_controls[task_key]["event"].set()
    
    client = manager.mtproto_client.client
    if not client.is_connected(): await client.connect()
    asyncio.create_task(_scrape_and_run(client, context.bot, msg.chat_id, parse_link(link), sub, is_monitor, jid, task_key))

async def handle_dls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not batch_controls: return await update.message.reply_text("📭 当前没有运行中的批量任务")
    lines = ["📑 <b>活跃下载任务列表:</b>"]
    for key, ctrl in batch_controls.items():
        status = "▶️ 运行中" if ctrl["event"].is_set() else "⏸ 已暂停"
        lines.append(f"任务 <code>#{ctrl['jid']}</code> | {status} | 标签: {ctrl['tag']}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def handle_dl_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not context.args: return
    tid = context.args[0]; target_key = f"{msg.chat_id}_{tid}"
    if target_key not in batch_controls: return await msg.reply_text("⚠️ 任务不存在")
    
    cmd = msg.text.lower()
    if "stop" in cmd: batch_controls[target_key]["event"].clear(); await msg.reply_text(f"⏸ 任务 #{tid} 已暂停")
    elif "continue" in cmd: batch_controls[target_key]["event"].set(); await msg.reply_text(f"▶️ 任务 #{tid} 已恢复")
    elif "no" in cmd: 
        batch_controls[target_key]["cancel"] = True; batch_controls[target_key]["event"].set()
        remove_active_job(int(tid)); await msg.reply_text(f"⏹ 任务 #{tid} 已取消")

# ===================== 5. 统一注册 =====================
def register(manager):
    init_db()
    handle_dl_command.manager = handle_dl_control.manager = handle_dls_command.manager = manager
    register_handler(CommandHandler("dl", handle_dl_command), __name__)
    register_handler(CommandHandler("dl_all", handle_dl_command), __name__)
    register_handler(CommandHandler("dls", handle_dls_command), __name__)
    register_handler(CommandHandler("dl_stop", handle_dl_control), __name__)
    register_handler(CommandHandler("dl_continue", handle_dl_control), __name__)
    register_handler(CommandHandler("dl_no", handle_dl_control), __name__)
    logger.info(f"✅ [{__MODULE_NAME__}] V1.0 已就绪")