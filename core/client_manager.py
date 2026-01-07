#openbot\core\client_manager.py
import logging
import asyncio
from typing import Optional
from telegram.ext import Application
from core.mtproto_client import MTProtoClient
from core.plugin_scanner import load_plugins

logger = logging.getLogger(__name__)

class ClientManager:
    def __init__(self, config, loop):
        self.config = config
        self.loop = loop
        self.bot_app: Optional[Application] = None
        self.mtproto_client: Optional[MTProtoClient] = None

    async def start_all(self) -> None:
        """启动系统：按顺序初始化 Bot 和 MTProto"""
        # 1. 初始化 Bot 实例
        # 💡 使用 builder 模式确保配置正确加载
        self.bot_app = Application.builder().token(self.config.get("BOT_TOKEN")).build()
        
        # 2. 注入管理器和配置到全局 bot_data
        # 💡 这确保了 mtlogin.py 等插件可以通过 context.bot_data['manager'] 访问
        self.bot_app.bot_data['manager'] = self
        self.bot_app.bot_data['config'] = self.config
        
        # 3. 启动 MTProto 持久化引擎
        # 💡 关键修改：增加超时判断，防止连接 Telegram 服务器时死等
        self.mtproto_client = MTProtoClient(
            api_id=int(self.config.get("API_ID")),
            api_hash=self.config.get("API_HASH"),
            loop=self.loop
        )
        
        try:
            # 💡 暴力启动：如果 15 秒内连不上，说明网络环境极差，直接报错不卡死
            success = await asyncio.wait_for(self.mtproto_client.start(), timeout=15.0)
            if success:
                logger.info("✅ MTProto 持久化引擎已就绪")
            else:
                logger.error("⚠️ MTProto 启动异常，部分核心功能（如强制抓取）将受限")
        except asyncio.TimeoutError:
            logger.error("❌ MTProto 启动连接超时：请确认服务器能直连 Telegram API (无代理模式)")

        # 4. 扫描并注册插件 (传入 manager 实例供 register 函数使用)
        load_plugins(self) 
        
        # 5. 启动 Bot 轮询
        await self.bot_app.initialize()
        await self.bot_app.start()
        await self.bot_app.updater.start_polling()
        logger.info("🤖 Bot 系统已完全启动，正在监听指令...")

    async def stop_all(self) -> None:
        """安全停止所有服务，并销毁内存残留"""
        logger.info("🛑 正在执行系统停机清理...")
        
        if self.bot_app:
            try:
                # 💡 停止轮询并释放 Bot 资源
                if self.bot_app.updater.running:
                    await self.bot_app.updater.stop()
                await self.bot_app.stop()
                await self.bot_app.shutdown()
            except Exception as e:
                logger.error(f"Bot 关闭异常: {e}")
                
        if self.mtproto_client:
            try:
                # 💡 断开 MTProto TCP 连接
                await self.mtproto_client.stop()
            except Exception as e:
                logger.error(f"MTProto 断开异常: {e}")
        
        # 💡 极致安全：强制清空内存引用，确保登录凭据不留痕迹
        self.bot_app = None
        self.mtproto_client = None

    @property
    def bot(self):
        """快捷访问底层的 Bot 对象"""
        return self.bot_app.bot if self.bot_app else None