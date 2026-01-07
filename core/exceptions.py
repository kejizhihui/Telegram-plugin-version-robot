#openbot\core\exceptions.py
class OpenBotBaseException(Exception):
    """所有 OpenBot 异常的基类"""
    def __init__(self, message: str = "发生 OpenBot 内部错误"):
        self.message = message
        super().__init__(self.message)

class ConfigMissingError(OpenBotBaseException):
    """配置项缺失或读取失败"""
    pass

class LoginFailedError(OpenBotBaseException):
    """MTProto 登录流程异常"""
    pass

class UnauthorizedError(OpenBotBaseException):
    """非管理员尝试执行敏感操作"""
    pass

class PluginLoadError(OpenBotBaseException):
    """插件扫描或动态加载失败"""
    pass

class NetworkTimeoutError(OpenBotBaseException):
    """请求 Telegram 服务器超时（通常是代理问题）"""
    pass