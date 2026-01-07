import asyncio
import json
import os
import logging
import hashlib
import re
import random
import shutil
from datetime import datetime
from telegram import Update, MessageEntity, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from core.command_registry import register_handler

# --- 插件元数据 ---
__MODULE_NAME__ = "超级转发器"
logger = logging.getLogger(__name__)

# --- 存储路径 ---
DATA_DIR = "转发数据"
TEMP_DIR = os.path.join(DATA_DIR, "temp_media")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

class ForwardEngineV3:
    def __init__(self, manager):
        self.manager = manager
        self.config = self._load("config.json", {"sources": {}, "destinations": {}, "rules": {}, "tasks": {}})
        self.cache = self._load("pending_cache.json", {"pending": {}, "hashes": {}, "last_cron": ""})
        self.media_groups = {}  # 内存缓存：{gid: [msgs]}
        self.running_locks = set()

    def _load(self, filename, default):
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: return json.load(f)
            except: return default
        return default

    def save(self):
        try:
            with open(os.path.join(DATA_DIR, "config.json"), 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            with open(os.path.join(DATA_DIR, "pending_cache.json"), 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=4)
        except Exception as e: logger.error(f"❌ 数据保存失败: {e}")

    # ================= 核心：内容搜刮与清洗 =================
    async def handle_incoming(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message: return
        msg = update.message
        chat_id = str(update.effective_chat.id)
        
        src_code = next((k for k, v in self.config["sources"].items() if str(v) == chat_id), None)
        if not src_code: return

        # 1. 深度内容去重 (忽略空格)
        text = msg.text or msg.caption or ""
        content_hash = hashlib.md5(re.sub(r'\s+', '', text).encode()).hexdigest()
        if content_hash in self.cache["hashes"]: return

        # 2. 相册聚合 (MediaGroup) 逻辑
        if msg.media_group_id:
            gid = msg.media_group_id
            if gid not in self.media_groups:
                self.media_groups[gid] = []
                asyncio.create_task(self._wait_and_store_group(gid, src_code, content_hash))
            self.media_groups[gid].append(msg)
        else:
            self._store_entry(src_code, msg, content_hash)

    async def _wait_and_store_group(self, gid, src_code, content_hash):
        await asyncio.sleep(3.5) # 等待相册传输完毕
        msgs = self.media_groups.pop(gid, [])
        if msgs:
            # 记录相册信息：取第一个作为主体，记录所有 file_id
            self._store_entry(src_code, msgs[0], content_hash, is_group=True, group_msgs=msgs)

    def _store_entry(self, src_code, msg, content_hash, is_group=False, group_msgs=None):
        if src_code not in self.cache["pending"]: self.cache["pending"][src_code] = []
        
        entry = {
            "msg_id": msg.message_id,
            "chat_id": msg.chat_id,
            "text": msg.text or msg.caption or "",
            "is_group": is_group,
            "media_type": "photo" if msg.photo else "video" if msg.video else "text",
            "timestamp": datetime.now().isoformat()
        }
        self.cache["pending"][src_code].append(entry)
        self.cache["hashes"][content_hash] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.save()

    # ================= 核心：破防重传分发器 =================
    async def dispatch(self, tid):
        if tid in self.running_locks: return
        self.running_locks.add(tid)
        task = self.config["tasks"].get(tid)
        if not task: 
            self.running_locks.remove(tid)
            return

        dst_ids = self.config["destinations"].get(task['dst'], [])
        rule = self.config["rules"].get(task['rule'], {})
        pending = self.cache["pending"].pop(task['src'], [])
        self.save()

        for item in pending:
            # 逻辑 A/B 清洗：含标签保留标签，无标签保留全文
            final_text = self._apply_cleaning(item['text'], rule)
            
            for target_id in dst_ids:
                try:
                    # 使用 copy_message 强制穿透
                    await self.manager.bot.copy_message(
                        chat_id=target_id,
                        from_chat_id=item['chat_id'],
                        message_id=item['msg_id'],
                        caption=final_text,
                        parse_mode="HTML"
                    )
                    await asyncio.sleep(1.2)
                except Exception as e:
                    logger.error(f"❌ 转发任务 {tid} 失败: {e}")
        
        self.running_locks.remove(tid)

    def _apply_cleaning(self, text, rule):
        suffix = f"\n\n{rule.get('suffix', '')}"
        tags = re.findall(r'#\w+', text)
        if tags and "#" in text:
            # 逻辑 A: 仅保留标签
            return " ".join(tags) + suffix
        # 逻辑 B: 保留原文
        return text + suffix

# ================= 业务指令集 =================

def register(manager):
    engine = ForwardEngineV3(manager)

    async def fw_src(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2: return await update.message.reply_html("格式: /fw_src 601 ID")
        engine.config["sources"][context.args[0]] = context.args[1]
        engine.save()
        await update.message.reply_html(f"✅ <b>源已绑定</b>: <code>{context.args[0]}</code>")

    async def fw_dst(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2: return await update.message.reply_html("格式: /fw_dst 701 ID1,ID2")
        engine.config["destinations"][context.args[0]] = [i.strip() for i in context.args[1].split(',')]
        engine.save()
        await update.message.reply_html(f"✅ <b>目标组已绑定</b>: <code>{context.args[0]}</code>")

    async def fw_rule(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 3: return await update.message.reply_html("格式: /fw_rule 801 20:00 后缀")
        engine.config["rules"][context.args[0]] = {"time": context.args[1], "suffix": " ".join(context.args[2:])}
        engine.save()
        await update.message.reply_html(f"✅ <b>清洗规则已建立</b>: <code>{context.args[0]}</code>")

    async def fw_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 3: return
        tid = f"9{random.randint(100, 999)}"
        engine.config["tasks"][tid] = {"src": context.args[0], "dst": context.args[1], "rule": context.args[2]}
        engine.save()
        await update.message.reply_html(f"🚀 <b>转发链路已开启</b>\n任务编号: <code>{tid}</code>")

    async def fw_task_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args: return
        tid = context.args[0]
        if tid in engine.config["tasks"]:
            del engine.config["tasks"][tid]
            engine.save()
            await update.message.reply_text(f"🗑️ 任务 {tid} 已销毁")

    async def fw_show_lib(update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = "🔄 <b>转发器资源快照 V3.8</b>\n━━━━━━━━━━━━━━━\n"
        msg += f"📥 <b>监控源 (6xx)</b>: {len(engine.config['sources'])} 个\n"
        msg += f"📤 <b>目标组 (7xx)</b>: {len(engine.config['destinations'])} 组\n"
        msg += f"⚙️ <b>清洗规 (8xx)</b>: {len(engine.config['rules'])} 条\n"
        msg += f"🚀 <b>运行中 (9xx)</b>: {len(engine.config['tasks'])} 条\n"
        await update.message.reply_html(msg)

    async def fw_cache_clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args: return
        src = context.args[0]
        engine.cache["pending"].pop(src, None)
        engine.save()
        await update.message.reply_text(f"🧹 源 {src} 的待发缓存已清空")

    # ================= 自动补救与调度 =================
    async def cron_loop():
        while True:
            try:
                now_str = datetime.now().strftime("%H:%M")
                # 补救机制：如果跨天或重启，检查上一次执行时间 (简化逻辑)
                for tid, info in list(engine.config["tasks"].items()):
                    rule = engine.config["rules"].get(info['rule'])
                    if rule and rule['time'] == now_str:
                        asyncio.create_task(engine.dispatch(tid))
                await asyncio.sleep(60)
            except: await asyncio.sleep(10)

    # 指令注册
    register_handler(CommandHandler("fw_src", fw_src), __name__)
    register_handler(CommandHandler("fw_dst", fw_dst), __name__)
    register_handler(CommandHandler("fw_rule", fw_rule), __name__)
    register_handler(CommandHandler("fw_task", fw_task), __name__)
    register_handler(CommandHandler("fw_task_del", fw_task_del), __name__)
    register_handler(CommandHandler("fw_show_lib", fw_show_lib), __name__)
    register_handler(CommandHandler("fw_cache_clean", fw_cache_clean), __name__)
    
    # 消息监听
    register_handler(MessageHandler(filters.ALL & (~filters.COMMAND), engine.handle_incoming), __name__)

    # 协程启动
    asyncio.get_event_loop().create_task(cron_loop())
    logger.info(f"✅ [{__MODULE_NAME__}] V1.0 已就绪")