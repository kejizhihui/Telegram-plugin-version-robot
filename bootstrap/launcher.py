import asyncio
import logging
import sys
from telethon import functions
from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes
from core.config_manager import ConfigManager
from core.validator import ConfigValidator
from core.client_manager import ClientManager
from core.logger import setup_logger

logger = logging.getLogger(__name__)

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# --- 新增：无效命令兜底处理器 ---
async def unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """拦截所有未匹配的斜杠指令"""
    # 仅针对私聊反馈，避免群组干扰
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "❌ <b>未知指令</b>\n"
            "系统无法识别该命令。请发送 /plugins 查看可用功能清单。",
            parse_mode="HTML"
        )

async def show_status_summary(manager):
    """打印启动后的汇总信息"""
    logger.info("\n📌 OpenBot 启动状态汇总")
    try:
        me = await manager.bot_app.bot.get_me()
        logger.info(f"Bot 状态：已连接 (@{me.username})")
        
        if manager.mtproto_client and manager.mtproto_client.client:
            try:
                await manager.mtproto_client.client(functions.updates.GetStateRequest())
            except:
                pass
            is_auth = await manager.mtproto_client.is_authorized()
            status = "已登录" if is_auth else "未授权 (需 /mtlogin)"
            logger.info(f"MTProto 状态：{status}")
        else:
            logger.info("MTProto 状态：未初始化")
    except Exception as e:
        logger.warning(f"⚠️ 状态汇总读取部分受阻: {e}")

def run_bot():
    setup_logger()
    config = ConfigManager()
    
    if not ConfigValidator(config).validate_all():
        return

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    manager = ClientManager(config, loop)

    try:
        # 1. 启动所有组件 (此处内部会完成所有插件的 register_handler 动作)
        loop.run_until_complete(manager.start_all())
        
        # 2. --- 【核心注入：无效命令兜底】 ---
        # 必须在 start_all 之后添加，确保它是 Handler 队列的最后一项
        manager.bot_app.add_handler(
            MessageHandler(filters.COMMAND, unknown_command_handler)
        )
        logger.info("🛡️ 全局无效指令兜底已激活")
        
        # 3. 显示汇总并运行
        loop.run_until_complete(show_status_summary(manager))
        
        logger.info("\n🚀 OpenBot 运行中... (按 Ctrl+C 退出)")
        loop.run_forever()

    except (KeyboardInterrupt, SystemExit):
        logger.info("\n🛑 接收到停止信号，准备安全退出...")
    except Exception as e:
        logger.error(f"\n❌ 系统运行崩溃: {e}", exc_info=True)
    finally:
        if manager:
            try:
                loop.run_until_complete(manager.stop_all())
            except:
                pass
        
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()
            print("\033[92m" + f"{logging.Formatter().formatTime(logging.makeLogRecord({}), '%Y-%m-%d %H:%M:%S')} - root - INFO - 👋 程序已完全安全退出" + "\033[0m")