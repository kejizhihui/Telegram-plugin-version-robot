import asyncio
import json
import os
import logging
import hashlib
import re
import random
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from core.command_registry import register_handler

# --- 插件元数据 ---
__MODULE_NAME__ = "超级转发器"
logger = logging.getLogger(__name__)

# --- 存储路径 ---
DATA_DIR = "转发数据"
os.makedirs(DATA_DIR, exist_ok=True)

class ForwardEngineV3:
    def __init__(self, manager):
        self.manager = manager
        self.config = self._load("config.json", {"sources": {}, "destinations": {}, "rules": {}, "tasks": {}})
        self.cache = self._load("pending_cache.json", {"pending": {}, "hashes": {}, "last_cron": ""})
        self.media_groups = {}  
        self.running_locks = set()
        self._needs_save = False

    def _load(self, filename, default):
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: return json.load(f)
            except: return default
        return default

    def save(self):
        """标记需要保存，由后台任务统一写入，防止频繁 IO 阻塞"""
        self._needs_save = True

    async def _io_loop(self):
        """每 5 秒检查一次是否需要持久化数据"""
        while True:
            if self._needs_save:
                try:
                    with open(os.path.join(DATA_DIR, "config.json"), 'w', encoding='utf-8') as f:
                        json.dump(self.config, f, ensure_ascii=False, indent=4)
                    with open(os.path.join(DATA_DIR, "pending_cache.json"), 'w', encoding='utf-8') as f:
                        json.dump(self.cache, f, ensure_ascii=False, indent=4)
                    self._needs_save = False
                except Exception as e:
                    logger.error(f"❌ 数据保存失败: {e}")
            await asyncio.sleep(5)

    # ================= 核心：内容搜刮与清洗 =================
    async def handle_incoming(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.effective_chat: return
        
        chat_id = str(update.effective_chat.id)
        # 【关键修复】: 只有在 sources 列表里的群组才会被拦截。
        # 这样你在私聊输入手机号时，这里会直接跳过，不会抢占输入流。
        src_code = next((k for k, v in self.config["sources"].items() if str(v) == chat_id), None)
        if not src_code: return 

        msg = update.message
        # 1. 深度内容去重 (忽略空格)
        text = msg.text or msg.caption or ""
        content_hash = hashlib.md5(re.sub(r'\s+', '', text).encode()).hexdigest()
        if content_hash in self.cache["hashes"]: return

        # 2. 相册聚合逻辑
        if msg.media_group_id:
            gid = msg.media_group_id
            if gid not in self.media_groups:
                self.media_groups[gid] = []
                asyncio.create_task(self._wait_and_store_group(gid, src_code, content_hash))
            self.media_groups[gid].append(msg)
        else:
            self._store_entry(src_code, msg, content_hash)

    async def _wait_and_store_group(self, gid, src_code, content_hash):
        await asyncio.sleep(3.5) 
        msgs = self.media_groups.pop(gid, [])
        if msgs:
            self._store_entry(src_code, msgs[0], content_hash, is_group=True)

    def _store_entry(self, src_code, msg, content_hash, is_group=False):
        if src_code not in self.cache["pending"]: self.cache["pending"][src_code] = []
        
        entry = {
            "msg_id": msg.message_id,
            "chat_id": msg.chat_id,
            "text": msg.text or msg.caption or "",
            "is_group": is_group,
            "timestamp": datetime.now().isoformat()
        }
        self.cache["pending"][src_code].append(entry)
        self.cache["hashes"][content_hash] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.save()

    # ================= 核心：破防重传分发器 =================
    async def dispatch(self, tid):
        if tid in self.running_locks: return
        self.running_locks.add(tid)
        try:
            task = self.config["tasks"].get(tid)
            if not task: return

            dst_ids = self.config["destinations"].get(task['dst'], [])
            rule = self.config["rules"].get(task['rule'], {})
            pending = self.cache["pending"].pop(task['src'], [])
            self.save()

            for item in pending:
                final_text = self._apply_cleaning(item['text'], rule)
                for target_id in dst_ids:
                    try:
                        # 使用 copy_message 强制穿透“禁止转发”限制
                        await self.manager.bot.copy_message(
                            chat_id=target_id,
                            from_chat_id=item['chat_id'],
                            message_id=item['msg_id'],
                            caption=final_text,
                            parse_mode="HTML"
                        )
                        await asyncio.sleep(1.2) # 防封控流控
                    except Exception as e:
                        logger.error(f"❌ 转发失败: {e}")
        finally:
            self.running_locks.remove(tid)

    def _apply_cleaning(self, text, rule):
        suffix = f"\n\n{rule.get('suffix', '')}"
        tags = re.findall(r'#\w+', text)
        if tags:
            # 逻辑 A: 仅保留标签
            return " ".join(tags) + suffix
        # 逻辑 B: 保留原文
        return text + suffix

# ================= 业务指令注册 =================

def register(manager):
    engine = ForwardEngineV3(manager)

    async def fw_src(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2: return await update.message.reply_html("格式: /fw_src 601 ID")
        engine.config["sources"][context.args[0]] = context.args[1]
        engine.save()
        await update.message.reply_html(f"✅ <b>源已绑定</b>: {context.args[0]}")

    async def fw_dst(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2: return await update.message.reply_html("格式: /fw_dst 701 ID1,ID2")
        engine.config["destinations"][context.args[0]] = [i.strip() for i in context.args[1].split(',')]
        engine.save()
        await update.message.reply_html(f"✅ <b>目标组已绑定</b>: {context.args[0]}")

    async def fw_rule(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 3: return await update.message.reply_html("格式: /fw_rule 801 20:00 后缀")
        engine.config["rules"][context.args[0]] = {"time": context.args[1], "suffix": " ".join(context.args[2:])}
        engine.save()
        await update.message.reply_html(f"✅ <b>规则已建立</b>: {context.args[0]}")

    async def fw_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 3: return
        tid = f"9{random.randint(100, 999)}"
        engine.config["tasks"][tid] = {"src": context.args[0], "dst": context.args[1], "rule": context.args[2]}
        engine.save()
        await update.message.reply_html(f"🚀 <b>任务已开启</b>: {tid}")

    async def fw_show_lib(update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = f"🔄 <b>转发器快照 V3.8</b>\n📥 源: {len(engine.config['sources'])}\n📤 目的: {len(engine.config['destinations'])}\n🚀 任务: {len(engine.config['tasks'])}"
        await update.message.reply_html(msg)

    async def cron_loop():
        while True:
            try:
                now_str = datetime.now().strftime("%H:%M")
                for tid, info in list(engine.config["tasks"].items()):
                    rule = engine.config["rules"].get(info['rule'])
                    if rule and rule['time'] == now_str:
                        asyncio.create_task(engine.dispatch(tid))
                await asyncio.sleep(60)
            except: await asyncio.sleep(10)

    # 注册处理器 (使用 Group 1 避免干扰核心登录逻辑)
    register_handler(CommandHandler("fw_src", fw_src), __name__)
    register_handler(CommandHandler("fw_dst", fw_dst), __name__)
    register_handler(CommandHandler("fw_rule", fw_rule), __name__)
    register_handler(CommandHandler("fw_task", fw_task), __name__)
    register_handler(CommandHandler("fw_show_lib", fw_show_lib), __name__)
    
    # 【关键修复】: 消息监听限制在非指令、非私聊输入
    register_handler(MessageHandler(filters.ChatType.GROUPS & (~filters.COMMAND), engine.handle_incoming), __name__)

    # 启动后台 IO 循环与任务调度
    loop = asyncio.get_event_loop()
    loop.create_task(engine._io_loop())
    loop.create_task(cron_loop())
    logger.info(f"✅ [{__MODULE_NAME__}] 工业级引擎已启动")
