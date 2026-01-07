#openbot\features\promo\smart_promo.py
import asyncio
import random
import json
import os
import logging
import time
import traceback
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from core.command_registry import register_handler
from core.utils import is_admin

# --- 插件元数据 ---
__MODULE_NAME__ = "智能推广"
logger = logging.getLogger(__name__)

# --- 存储路径 ---
DATA_DIR = "推广数据"
os.makedirs(DATA_DIR, exist_ok=True)

# 运行时全局锁定状态
SAVE_SESSION = {}  # {user_id: {"expire": timestamp}}

class SmartPromoEngine:
    def __init__(self, manager):
        self.manager = manager
        self.contents = self._load("内容库.json")
        self.modes = self._load("模式库.json")
        self.groups = self._load("群组库.json")
        self.tasks = self._load("任务监控.json")
        self.counters = {tid: 0 for tid in self.tasks}

    def _load(self, filename):
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: return {}
        return {}

    def save(self):
        mapping = {
            "内容库.json": self.contents, 
            "模式库.json": self.modes,
            "群组库.json": self.groups, 
            "任务监控.json": self.tasks
        }
        for f, data in mapping.items():
            with open(os.path.join(DATA_DIR, f), 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)

    async def run_worker(self, tid):
        task = self.tasks.get(tid)
        if not task: return
        content = self.contents.get(task['content_id'])
        target_ids = self.groups.get(task['group_id'], [])
        if not content or not target_ids: return

        ts = f"\n\n🕒 动态校验: {datetime.now().strftime('%H:%M:%S')}"
        caption = (content.get('text', '') + ts).strip()

        success = 0
        for gid in target_ids:
            try:
                await self.manager.bot.copy_message(
                    chat_id=gid, 
                    from_chat_id=content['from_chat_id'],
                    message_id=content['message_id'], 
                    caption=caption, 
                    parse_mode="HTML"
                )
                success += 1
                await asyncio.sleep(2.0)
            except Exception as e:
                logger.error(f"❌ [推广至 {gid}] 失败: {e}")
        
        task['hits'] = task.get('hits', 0) + 1
        task['total_sent'] = task.get('total_sent', 0) + success
        self.save()

# ===================== 业务处理器 =====================

async def handle_tg_save_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/tg_save - 开启30秒独占捕获模式"""
    user_id = update.effective_user.id
    SAVE_SESSION[user_id] = {"expire": time.time() + 30}
    await update.message.reply_html(
        "⏳ <b>进入捕获模式 (30s 独占)</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "请直接 <b>发送或转发</b> 一个素材给我。\n"
        "系统将锁定其原始 ID，不需要回复指令。"
    )

async def handle_capture_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """核心逻辑：独占捕获优先，监听计数随后"""
    if not update.message: return
    user_id = update.effective_user.id
    engine = getattr(handle_capture_logic, "engine", None)

    # 1. 检查锁定会话
    session = SAVE_SESSION.get(user_id)
    if session and time.time() <= session["expire"]:
        target = update.message
        f_chat_id, f_msg_id = None, None
        if target.forward_origin:
            origin = target.forward_origin
            if hasattr(origin, 'chat'): f_chat_id, f_msg_id = origin.chat.id, origin.message_id
            elif hasattr(origin, 'sender_user'): f_chat_id, f_msg_id = target.chat_id, target.message_id
        if not f_chat_id: f_chat_id, f_msg_id = target.chat_id, target.message_id

        existing = [int(k) for k in engine.contents.keys() if k.isdigit()]
        cid = str(max(existing) + 1 if existing else 101)
        engine.contents[cid] = {
            "message_id": f_msg_id, "from_chat_id": f_chat_id,
            "text": target.caption or target.text or "",
            "type": "media" if (target.photo or target.video or target.document) else "text"
        }
        engine.save()
        if user_id in SAVE_SESSION: del SAVE_SESSION[user_id]
        return await update.message.reply_html(f"✅ <b>素材捕获成功</b>\n编号: <code>{cid}</code>\n源: <code>{f_chat_id}</code>")

    # 2. 监听逻辑
    if update.effective_chat.type != "private":
        chat_id = str(update.effective_chat.id)
        for tid, task in list(engine.tasks.items()):
            if chat_id in [str(i) for i in engine.groups.get(task['group_id'], [])]:
                engine.counters[tid] = engine.counters.get(tid, 0) + 1
                mode = engine.modes.get(task['mode_id'])
                if mode and engine.counters[tid] >= mode['value']:
                    engine.counters[tid] = 0
                    asyncio.create_task(engine.run_worker(tid))

async def handle_tg_show_lib(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/tg_show_lib - 综合数据库仪表盘"""
    engine = getattr(handle_tg_show_lib, "engine", None)
    res = ["📑 <b>智能推广数据库仪表盘</b>", "━━━━━━━━━━━━━━━"]

    # 1. 内容库展示
    res.append("📦 <b>内容素材库 (1xx)</b>")
    if not engine.contents: res.append("  (空)")
    for k, v in engine.contents.items():
        m_type = "🖼" if v.get('type') == 'media' else "📝"
        preview = v.get('text', '')[:15].replace('\n', ' ')
        res.append(f"  <code>{k}</code> {m_type} {preview}...")

    # 2. 模式库展示
    res.append("\n⚙️ <b>触发模式库 (2xx)</b>")
    if not engine.modes: res.append("  (空)")
    for k, v in engine.modes.items():
        res.append(f"  <code>{k}</code> ➔ 满 {v['value']} 条消息触发")

    # 3. 群组库展示
    res.append("\n👥 <b>群组矩阵库 (3xx)</b>")
    if not engine.groups: res.append("  (空)")
    for k, v in engine.groups.items():
        res.append(f"  <code>{k}</code> ➔ 包含 {len(v)} 个目标群")

    res.append("\n━━━━━━━━━━━━━━━")
    res.append("💡 <i>使用 /tg_task_list 查看运行中的任务</i>")
    await update.message.reply_html("\n".join(res))

async def handle_tg_mode_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    engine = getattr(handle_tg_mode_set, "engine", None)
    if len(context.args) < 3: return await update.message.reply_html("❌ <code>/tg_mode_set 201 inc 10</code>")
    mid, val = context.args[0], int(context.args[2])
    engine.modes[mid] = {"type": "inc", "value": val}
    engine.save()
    await update.message.reply_html(f"✅ 模式 <code>{mid}</code> 已设为 <b>{val}</b> 条消息触发")

async def handle_tg_group_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    engine = getattr(handle_tg_group_reg, "engine", None)
    if len(context.args) < 2: return await update.message.reply_html("❌ <code>/tg_group_reg 301 ID1,ID2</code>")
    gid, ids_str = context.args[0], context.args[1]
    id_list = [i.strip() for i in ids_str.split(',')]
    engine.groups[gid] = id_list
    engine.save()
    await update.message.reply_html(f"✅ 矩阵 <code>{gid}</code> 已登记 {len(id_list)} 个群组")

async def handle_tg_push(update: Update, context: ContextTypes.DEFAULT_TYPE):
    engine = getattr(handle_tg_push, "engine", None)
    if len(context.args) < 3: return await update.message.reply_html("❌ <code>/tg_push 101 201 301</code>")
    tid = f"5{random.randint(100, 999)}"
    engine.tasks[tid] = {"content_id": context.args[0], "mode_id": context.args[1],
                         "group_id": context.args[2], "hits": 0, "total_sent": 0, "freq_range": [30, 120]}
    engine.counters[tid] = 0
    engine.save()
    await update.message.reply_html(f"🚀 <b>任务 {tid} 开启</b>\n联动: 内容{context.args[0]} ➔ 模式{context.args[1]} ➔ 矩阵{context.args[2]}")

async def handle_tg_task_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    engine = getattr(handle_tg_task_list, "engine", None)
    if not engine.tasks: return await update.message.reply_text("📭 无活跃推广任务")
    res = ["📊 <b>推广任务实时监控</b>", "━━━━━━━━━━━━━━━"]
    for tid, t in engine.tasks.items():
        res.append(f"🆔 {tid} | 计数: {engine.counters.get(tid,0)} | 已发: {t['total_sent']}")
    await update.message.reply_text("\n".join(res), parse_mode="HTML")

async def handle_tg_task_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    engine = getattr(handle_tg_task_del, "engine", None)
    if context.args and context.args[0] in engine.tasks:
        del engine.tasks[context.args[0]]
        engine.save()
        await update.message.reply_text(f"🛑 任务 {context.args[0]} 已停用")

# ===================== 统一注册入口 =====================

def register(manager):
    engine = SmartPromoEngine(manager)
    cmd_map = {
        "tg_save": handle_tg_save_start,
        "tg_show_lib": handle_tg_show_lib,
        "tg_mode_set": handle_tg_mode_set,
        "tg_group_reg": handle_tg_group_reg,
        "tg_push": handle_tg_push,
        "tg_task_list": handle_tg_task_list,
        "tg_task_del": handle_tg_task_del
    }
    for cmd, func in cmd_map.items():
        setattr(func, "engine", engine)
        register_handler(CommandHandler(cmd, func), __name__)

    setattr(handle_capture_logic, "engine", engine)
    register_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_capture_logic), __name__)
    logger.info(f"✅ [{__MODULE_NAME__}] V1.0 数据库仪表盘版已就绪")