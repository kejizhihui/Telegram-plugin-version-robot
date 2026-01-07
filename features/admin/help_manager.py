# openbot\features\admin\help_manager.py
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from core.command_registry import register_handler
from core.utils import is_admin

logger = logging.getLogger(__name__)

# 插件名称
__MODULE_NAME__ = "开发手册"

# --- 核心文档内容 ---
PROJECT_DOCS = (
    "🚀 <b>OpenBot 2026 项目架构说明</b>\n\n"
    "本系统采用 <b>Bot API</b> + <b>MTProto</b> 双引擎，支持热重载。\n\n"
    "📂 <b>目录结构：</b>\n"
    "• <code>core/</code>: 核心驱动层 (禁止改动)\n"
    "• <code>features/</code>: 官方插件层\n\n"
    "🛡️ <b>开发准则：</b>\n"
    "1️⃣ <b>资源获取</b>: 必须通过注入的 <code>manager</code> 对象访问配置和客户端。\n"
    "2️⃣ <b>ID 格式</b>: 文件路径 ID 禁止使用括号 <code>()</code>。\n"
    "3️⃣ <b>注册逻辑</b>: 使用 <code>register(manager)</code> 结构。"
)

# 核心修改：模板现在改为注入模式
CODE_TEMPLATE = (
    "__MODULE_NAME__ = \"新功能名称\"\n\n"
    "async def handle_func(update, context):\n"
    "    manager = getattr(handle_func, 'manager', None)\n"
    "    await update.message.reply_text('✅ 引擎已就绪')\n\n"
    "def register(manager):\n"
    "    handle_func.manager = manager\n"
    "    register_handler(CommandHandler('cmd', handle_func), __name__)"
)

# --- 业务处理器 ---

async def handle_cj(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    # 获取注入的 manager 
    manager = getattr(handle_cj, "manager", None) or context.bot_data.get('manager')
    config = manager.config if manager else context.bot_data.get('config')

    # 权限校验
    if not is_admin(user_id, config):
        await update.message.reply_text("🚫 该手册仅限管理员查看。")
        return

    # 发送项目说明
    await update.message.reply_text(PROJECT_DOCS, parse_mode="HTML")
    
    # 发送代码模板
    template_msg = (
        "📄 <b>V2.5 标准插件模板</b>\n"
        f"<pre><code class=\"language-python\">{CODE_TEMPLATE}</code></pre>"
    )
    await update.message.reply_text(template_msg, parse_mode="HTML")

# ===================== 统一注册入口 =====================

def register(manager):
    """
    修改为注入模式：
    1. 绑定 manager 方便 handle_cj 使用
    2. 注册 CommandHandler
    """
    handle_cj.manager = manager
    register_handler(CommandHandler("cj", handle_cj), __name__)

# 注意：不要在末尾手动调用 register()，由 scanner 自动调用
    logger.info(f"✅ [{__MODULE_NAME__}] V1.0 开发手册插件已就绪")