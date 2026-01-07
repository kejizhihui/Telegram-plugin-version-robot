import logging
import os
import asyncio
import re
import traceback
import time
from telethon import events, types
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from core.command_registry import register_handler
from core.utils import is_admin

logger = logging.getLogger(__name__)

__MODULE_NAME__ = "MTProto转发自动机器人保存引擎"

# 全局存储，用于追踪用户的当前批次
USER_BATCH_SESSIONS = {}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ===================== UI 智能看板 (批次版) =====================
class IndependentUI:
    def __init__(self, bot, chat_id, title="📥 批量秒下任务"):
        self.bot = bot
        self.chat_id = chat_id
        self.title = title
        self.tasks = {}
        self.order = []
        self.status_msg = None
        self.last_update = 0
        self.stats = {"total": 0, "done": 0, "fail": 0}
        self._lock = asyncio.Lock()

    async def update(self, tid, icon, text, force=False):
        if tid not in self.tasks: self.order.append(tid)
        self.tasks[tid] = f"{icon} <code>{tid}</code> | {text}"
        
        now = time.time()
        if not force and now - self.last_update < 1.5: return

        async with self._lock:
            self.last_update = time.time()
            display_limit = 8
            active_lines = [self.tasks[i] for i in self.order[-display_limit:]]
            task_list_str = "\n".join(active_lines)
            summary = f"\n... 其余 {len(self.order)-display_limit} 个文件" if len(self.order) > display_limit else ""
            
            text_out = (
                f"🚀 <b>{self.title}</b>\n"
                f"📊 状态: {self.stats['done']} / {self.stats['total']} 完成\n"
                f"━━━━━━━━━━━━━━━\n"
                f"{task_list_str}{summary}\n"
                f"━━━━━━━━━━━━━━━"
            )
            try:
                if self.status_msg:
                    await self.status_msg.edit_text(text_out, parse_mode="HTML")
                else:
                    self.status_msg = await self.bot.send_message(self.chat_id, text_out, parse_mode="HTML")
            except: pass

# ===================== MTProto 下载逻辑 (原始ID + 频道名) =====================
async def mtproto_download_logic(client, message, ui):
    msg_id = message.id
    try:
        # 1. 解析原始 ID 和名字 (不删前缀)
        source_id = "Unknown"
        chat_name = "Direct_Transfer"
        
        if message.forward:
            if message.forward.chat:
                source_id = str(message.forward.chat_id) # 💡 保留原始 ID，如 -100...
                chat_name = getattr(message.forward.chat, 'title', 'Channel')
            elif message.forward.sender:
                source_id = str(message.forward.sender_id)
                chat_name = f"User_{source_id}"
        else:
            source_id = str(message.chat_id)
            try:
                ent = await client.get_entity(message.chat_id)
                chat_name = getattr(ent, 'title', 'Private')
            except: pass

        # 2. 构造文件夹：download / 原始ID / 频道名字
        safe_chat = re.sub(r'[\\/:*?"<>|]', "_", str(chat_name))
        save_dir = os.path.join(BASE_DIR, "download", source_id, safe_chat)
        os.makedirs(save_dir, exist_ok=True)

        # 3. 文件名救助
        filename = f"{msg_id}"
        if isinstance(message.media, types.MessageMediaDocument):
            for a in message.media.document.attributes:
                if isinstance(a, types.DocumentAttributeFilename):
                    filename = a.file_name
        elif isinstance(message.media, types.MessageMediaPhoto):
            filename = f"photo_{msg_id}.jpg"

        path = os.path.join(save_dir, filename)

        if os.path.exists(path):
            ui.stats["done"] += 1
            await ui.update(msg_id, "🟢", "已存在", force=True)
            return

        await ui.update(msg_id, "🟡", "下载中", force=False)
        
        # 4. 执行下载 ( temp 后缀确保原子性)
        temp_path = path + ".temp"
        await client.download_media(message, file=temp_path)

        if os.path.exists(temp_path):
            os.rename(temp_path, path)
            ui.stats["done"] += 1
            await ui.update(msg_id, "✅", "完成", force=True)
        else: raise Exception("Save Fail")

    except Exception as e:
        ui.stats["fail"] += 1
        await ui.update(msg_id, "🔴", f"失败: {str(e)[:15]}", force=True)

# ===================== MTProto 底层监听 (批次判定) =====================
async def mt_on_new_message(event):
    if not event.is_private: return
    manager = mt_on_new_message.manager
    if not is_admin(event.sender_id, manager.config): return
    if not event.message.media: return

    user_id = event.sender_id
    now = time.time()
    
    # 3 秒批次判定逻辑
    session = USER_BATCH_SESSIONS.get(user_id)
    if session and (now - session["last_msg_time"] < 3.0):
        ui = session["ui"]
        session["last_msg_time"] = now
    else:
        ui = IndependentUI(manager.bot_app.bot, user_id)
        USER_BATCH_SESSIONS[user_id] = {"ui": ui, "last_msg_time": now}
    
    ui.stats["total"] += 1
    await ui.update(event.message.id, "🔍", "准备中", force=True)
    asyncio.create_task(mtproto_download_logic(event.client, event.message, ui))

# ===================== 注册入口 =====================
# ===================== 状态指令 (修复看板分类的关键) =====================
async def handle_at_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/at - 查看下载引擎状态"""
    await update.effective_message.reply_text(
        "🛡️ <b>MTProto 自动保存引擎 (V5.5)</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "● 状态: 🟢 运行中\n"
        "● 模式: 原始ID/文件夹分类\n"
        "● 核心: 实时监听批次下载", 
        parse_mode="HTML"
    )

# ===================== 注册入口 (彻底修复分类与崩溃) =====================
def register(manager):
    try:
        # 1. 挂载 MTProto 底层事件
        client = manager.mtproto_client.client
        mt_on_new_message.manager = manager
        
        # 物理防重：先移除再添加，防止重复挂载导致双倍下载
        client.remove_event_handler(mt_on_new_message)
        client.add_event_handler(mt_on_new_message, events.NewMessage)
        
        # 2. 注册指令入口 (让扫描器能抓到 __MODULE_NAME__)
        # 注意：这里使用了 CommandHandler，请确保文件顶部有 from telegram.ext import CommandHandler
        from telegram.ext import CommandHandler
        register_handler(CommandHandler("at", handle_at_status), __name__)
        
        logger.info(f"✅ [{__MODULE_NAME__}] V1.0 已就绪")
        
    except Exception as e:
        logger.error(f"❌ [{__MODULE_NAME__}] 注册崩溃: {traceback.format_exc()}")
        raise e # 抛出异常让 scanner 捕获并显示在日志中