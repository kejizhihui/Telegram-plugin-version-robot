#openbot\core\validator.py
import logging
from core.exceptions import ConfigMissingError

logger = logging.getLogger(__name__)

class ConfigValidator:
    def __init__(self, config):
        self.config = config

    def validate_all(self) -> bool:
        """校验所有必要配置项"""
        results = [
            self._validate_bot_token(),
            self._validate_api_id_hash(),
            self._validate_admin_id()
        ]
        return all(results)
    
    def _validate_bot_token(self) -> bool:
        token = self.config.get("BOT_TOKEN")
        if not token or ":" not in token:
            logger.error("❌ 配置错误: BOT_TOKEN 格式不正确")
            return False
        return True
    
    def _validate_api_id_hash(self) -> bool:
        api_id = self.config.get("API_ID")
        api_hash = self.config.get("API_HASH")
        if not (api_id and api_id.isdigit()):
            logger.error("❌ 配置错误: API_ID 必须是纯数字")
            return False
        if not (api_hash and len(api_hash) == 32):
            logger.error("❌ 配置错误: API_HASH 必须是 32 位字符串")
            return False
        return True

    def _validate_admin_id(self) -> bool:
        """新增：确保配置了管理员 ID"""
        admin_id = self.config.get("ADMIN_ID")
        if not admin_id:
            logger.warning("⚠️ 警告: 未在 .env 中配置 ADMIN_ID，所有管理功能将不可用")
            # 这里返回 True 是因为这不影响启动，但会影响后续功能
        return True