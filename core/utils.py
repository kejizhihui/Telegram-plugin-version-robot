# openbot\core\utils.py
import re
import logging

logger = logging.getLogger(__name__)

def is_valid_phone(phone: str) -> bool:
    """校验手机号格式（E.164 标准）"""
    pattern = r"^\+[1-9]\d{1,14}$"
    return re.match(pattern, phone) is not None

def mask_string(s: str, visible_chars: int = 6) -> str:
    """字符串脱敏处理"""
    if not s or len(s) <= visible_chars * 2:
        return "******"
    return f"{s[:visible_chars]}...{s[-visible_chars:]}"

def is_admin(user_id: int, config) -> bool:
    """
    核心权限校验：判断用户是否为管理员
    适配：同时支持 Bot API 和 MTProto 的用户 ID 校验
    """
    # 尝试兼容 ADMIN_ID 和 ADMIN_LIST
    admin_id = config.get("ADMIN_ID")
    if not admin_id:
        logger.warning(f"⚠️ 未配置 ADMIN_ID，拦截来自 {user_id} 的访问")
        return False
    
    # 统一转为字符串并去空格进行比对，防止 .env 读取格式差异
    return str(user_id).strip() == str(admin_id).strip()

