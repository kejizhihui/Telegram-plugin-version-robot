import logging
import os
import asyncio
from telethon import TelegramClient
from typing import Optional

logger = logging.getLogger(__name__)

class MTProtoClient:
    def __init__(self, api_id: int, api_hash: str, loop=None):
        self.api_id = api_id
        self.api_hash = api_hash
        
        session_dir = "sessions"
        os.makedirs(session_dir, exist_ok=True)
        self.session_path = os.path.join(session_dir, "openbot") 
        
        # 💡 对齐 loop 并保持暴力连接参数
        self.client = TelegramClient(
            self.session_path,
            api_id,
            api_hash,
            loop=loop,
            connection_retries=10, 
            retry_delay=2,
            auto_reconnect=True,
            sequential_updates=False,   
            timeout=10,
            receive_updates=True
        )
    
    async def start(self) -> bool:
        try:
            if not self.client.is_connected():
                await asyncio.wait_for(self.client.connect(), timeout=10.0)
            
            self.client.max_concurrent_transfers = 16
            
            # 💡 只有在已授权情况下才拉取 dialogs，否则登录前拉取会报错
            if await self.client.is_user_authorized():
                await self.client.get_dialogs(limit=1)
            
            logger.info("✅ MTProto 物理引擎已就绪")
            return True
        except Exception as e:
            logger.error(f"❌ MTProto 启动连接失败: {e}")
            return False

    async def is_authorized(self) -> bool:
        try:
            if not self.client.is_connected():
                await asyncio.wait_for(self.client.connect(), timeout=5.0)
            return await self.client.is_user_authorized()
        except:
            return False

    async def stop(self) -> None:
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            logger.info("🔌 MTProto 已安全断开")