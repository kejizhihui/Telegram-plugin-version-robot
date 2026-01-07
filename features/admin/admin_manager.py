import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from core.command_registry import register_handler
from core.utils import is_admin

logger = logging.getLogger(__name__)

__MODULE_NAME__ = "用户管理"

# --- 业务处理器 ---

async def handle_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """添加管理员权限"""
    manager = getattr(handle_add_admin, "manager", None) or context.bot_data.get('manager')
    config = manager.config
    
    if not is_admin(update.effective_user.id, config):
        await update.message.reply_text("❌ 无权限！")
        return
        
    if not context.args:
        await update.message.reply_text("💡 用法：/add_admin 用户ID")
        return
        
    try:
        new_id = int(context.args[0])
        if 'ADMIN_LIST' not in config: config['ADMIN_LIST'] = []
        
        if new_id not in config['ADMIN_LIST']:
            config['ADMIN_LIST'].append(new_id)
            # 💡 核心修复：修改内存后立即触发 manager 的持久化保存
            if hasattr(manager, "save_config"):
                manager.save_config() 
            await update.message.reply_text(f"✅ 已添加管理员: `{new_id}`")
        else:
            await update.message.reply_text("ℹ️ 该用户已在列表中")
    except ValueError:
        await update.message.reply_text("⚠️ ID 必须是纯数字")

async def handle_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看管理团队列表"""
    manager = getattr(handle_admins, "manager", None) or context.bot_data.get('manager')
    config = manager.config
    
    if not is_admin(update.effective_user.id, config): return
    
    admins = config.get('ADMIN_LIST', [])
    super_admin = config.get('SUPER_ADMIN')
    
    msg = (
        f"👑 **超级管理**: `{super_admin}`\n"
        f"🛠️ **管理员列表**: `{len(admins)}`人\n"
        f"━━━━━━━━━━━━━━\n"
        + "\n".join([f"• `{a}`" for a in admins])
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def handle_groupinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """高级群组信息统计 (MTProto 暴力引擎)"""
    manager = getattr(handle_groupinfo, "manager", None) or context.bot_data.get('manager')
    if not is_admin(update.effective_user.id, manager.config): return
    
    status_msg = await update.message.reply_text("🔍 正在通过 MTProto 抓取深度数据...")
    
    if manager and manager.mtproto_client and manager.mtproto_client.client:
        try:
            client = manager.mtproto_client.client
            from telethon.tl.functions.channels import GetFullChannelRequest
            
            # 使用 update.effective_chat.id，Telethon 会自动处理映射
            full = await client(GetFullChannelRequest(update.effective_chat.id))
            
            title = full.chats[0].title
            count = full.full_chat.participants_count
            online = getattr(full.full_chat, 'online_count', '未知')
            
            msg = (
                f"📊 **群组信息统计**\n"
                f"━━━━━━━━━━━━━━\n"
                f"🏷️ 群组名称: `{title}`\n"
                f"👥 成员总数: `{count}`\n"
                f"🌐 在线人数: `{online}`\n"
                f"🆔 内部 ID: `{update.effective_chat.id}`"
            )
            await status_msg.edit_text(msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"MTProto 抓取失败: {e}")
            await status_msg.edit_text(f"❌ MTProto 解析失败: {str(e)}")
    else:
        await status_msg.edit_text("❌ MTProto 引擎未就绪，无法获取深度数据。")

# --- 💡 补全缺失的函数以修复 NameError ---

async def handle_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """封禁用户 (简易示例)"""
    # 权限校验略... 
    await update.message.reply_text("🚫 该功能需配合群组管理权限使用。")

# ===================== 统一注册入口 =====================

def register(manager):
    """V2.5 注册入口：批量注入 manager 并挂载指令"""
    # 💡 修复：确保这里的列表与上面定义的函数名完全匹配
    handlers = [handle_add_admin, handle_admins, handle_groupinfo, handle_ban]
    
    for h in handlers:
        h.manager = manager
    
    register_handler(CommandHandler("add_admin", handle_add_admin), __name__)
    register_handler(CommandHandler("admins", handle_admins), __name__)
    register_handler(CommandHandler("groupinfo", handle_groupinfo), __name__)
    register_handler(CommandHandler("ban", handle_ban), __name__)

    logger.info(f"✅ [{__MODULE_NAME__}] V1.0 管理员功能已就绪")