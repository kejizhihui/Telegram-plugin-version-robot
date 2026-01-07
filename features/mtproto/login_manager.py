import logging
import asyncio
import traceback
from telegram import Update 
from telegram.ext import ContextTypes, MessageHandler, CommandHandler, filters
from core.utils import is_valid_phone, is_admin
from core.command_registry import register_handler

# 1. 初始化
logger = logging.getLogger(__name__)
user_login_states = {}

# 元数据定义 (用于看板显示标题)
__MODULE_NAME__ = "MTProto 登录管理器"

async def _clean_user_state(user_id: int) -> None:
    """清理内存中的登录中间状态"""
    if user_id in user_login_states:
        del user_login_states[user_id]
        logger.info(f"🧹 已从内存销毁用户 {user_id} 的登录凭据")

async def mtlogin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/mtlogin 指令入口"""
    user_id = update.effective_user.id
    # 优先从函数属性获取 manager
    manager = getattr(mtlogin_handler, "manager", None)
    
    if not is_admin(user_id, manager.config):
        await update.message.reply_html("🚫 <b>权限不足</b>")
        return

    status_msg = await update.message.reply_html("🔍 <b>正在查询 MTProto 会话状态...</b>")
    client_wrapper = manager.mtproto_client

    try:
        # 检查是否已登录
        is_auth = await asyncio.wait_for(client_wrapper.is_authorized(), timeout=5.0)
        if is_auth:
            me = await client_wrapper.client.get_me()
            await status_msg.edit_text(
                f"✅ <b>MTProto 已就绪</b>\n"
                f"👤 账户：<code>{me.first_name}</code>\n"
                f"📱 手机：<code>+{me.phone}</code>",
                parse_mode="HTML"
            )
            return
    except:
        pass

    # 进入状态机
    user_login_states[user_id] = {"step": "wait_phone", "manager": manager}
    await status_msg.edit_text("🚀 <b>开始登录流程</b>\n请输入手机号 (带国家码，例如 +86138...)：", parse_mode="HTML")

async def handle_login_steps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理登录步骤：自动撤回敏感消息 + 内存销毁"""
    user_id = update.effective_user.id
    if user_id not in user_login_states:
        return
    
    state = user_login_states[user_id]
    text = update.message.text.strip()
    # 核心修复：确保从 state 或属性稳定获取 manager
    manager = state.get("manager") or getattr(handle_login_steps, "manager", None)
    client = manager.mtproto_client.client 

    # 💡 【物理撤回】保护隐私
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"无法撤回消息: {e}")

    try:
        # 步骤 1：处理手机号
        if state["step"] == "wait_phone":
            if not is_valid_phone(text):
                await update.message.reply_html("⚠️ <b>格式错误</b>，请重新输入（需带+号和国家码）：")
                return
            
            state["phone"] = text
            sent_code = await client.send_code_request(text)
            state["phone_code_hash"] = sent_code.phone_code_hash
            state["step"] = "wait_code"
            await update.message.reply_html("📩 <b>验证码已发送</b>\n(已撤回您的手机号，请在此回复验证码)：")

        # 步骤 2：处理验证码
        elif state["step"] == "wait_code":
            try:
                await client.sign_in(
                    phone=state["phone"], 
                    phone_code_hash=state["phone_code_hash"], 
                    code=text
                )
                await _login_success_feedback(update, user_id)
            except Exception as e:
                if "password" in str(e).lower():
                    state["step"] = "wait_password"
                    await update.message.reply_html("🔐 <b>两步验证</b>\n检测到二级密码，请输入：\n(您的验证码已撤回)")
                else: 
                    await _clean_user_state(user_id)
                    await update.message.reply_html(f"❌ <b>验证码错误</b>\n流程已中断。请重新执行 /mtlogin")

        # 步骤 3：处理二级密码
        elif state["step"] == "wait_password":
            await client.sign_in(password=text)
            await _login_success_feedback(update, user_id)

    except Exception as e:
        logger.error(f"登录失败: {traceback.format_exc()}")
        await _clean_user_state(user_id)
        await update.message.reply_html(f"❌ <b>操作失败</b>\n原因：<code>{str(e)}</code>")

async def _login_success_feedback(update: Update, user_id: int):
    """成功反馈 + 内存销毁"""
    await update.message.reply_html(
        "✨ <b>MTProto 授权成功！</b>\n\n"
        "✅ 会话已保存至本地文件\n"
        "🧹 内存中间件已清理完毕。"
    )
    await _clean_user_state(user_id)

# ===================== 注册入口 =====================

def register(manager):
    # 1. 预挂载资源，防止 handle_login_steps 找不到 manager
    mtlogin_handler.manager = manager
    handle_login_steps.manager = manager
    
    # 2. 注册主指令
    register_handler(CommandHandler("mtlogin", mtlogin_handler), __name__)
    
    # 3. 核心修复：注册 MessageHandler 并显式绑定 __name__
    # 这样系统看板就能识别到这个监听器属于“MTProto 登录管理器”
    register_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, 
            handle_login_steps
        ), 
        __name__
    )
    
    logger.info(f"✅ [{__MODULE_NAME__}] V1.0 已就绪")