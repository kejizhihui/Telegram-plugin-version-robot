import logging
import sys
from typing import List, Any, Dict

logger = logging.getLogger(__name__)

# --- 全局存储容器 ---
# 使用全局变量确保热重载时数据能被清空和重建
GLOBAL_HANDLERS: List[Any] = []
# 💡 关键修改：PLUGIN_MAP 现在存储结构化字典，不再是简单的 set
PLUGIN_MAP: Dict[str, Dict[str, Any]] = {}

def get_handlers(): return GLOBAL_HANDLERS
def get_plugin_map(): return PLUGIN_MAP

def clear_handlers():
    global GLOBAL_HANDLERS, PLUGIN_MAP
    GLOBAL_HANDLERS.clear()
    PLUGIN_MAP.clear()
    logger.debug("🧹 注册器账本已清空")

def register_handler(handler: Any, module_name: str = None):
    """
    插件注册核心函数
    handler: Bot API 的 Handler 对象
    module_name: 插件的模块路径
    """
    # 1. 存入待加载列表（用于 Bot 挂载）
    if handler and handler not in GLOBAL_HANDLERS:
        GLOBAL_HANDLERS.append(handler)
    
    # 2. 提取插件唯一标识
    plugin_key = module_name.split('.')[-1] if module_name else "未分类"
    
    # 3. 💡 初始化结构化字典
    if plugin_key not in PLUGIN_MAP:
        # 尝试从模块中获取中文别名
        module_obj = sys.modules.get(module_name)
        alias = getattr(module_obj, "__MODULE_NAME__", plugin_key.replace('_', ' ').title())
        
        PLUGIN_MAP[plugin_key] = {
            "alias": alias,           # 中文名称
            "file": f"{plugin_key}.py", # 文件名
            "cmds": set()             # 真实指令集
        }
    
    # 4. 自动提取 / 指令
    if handler:
        cmd_attr = getattr(handler, 'commands', getattr(handler, 'command', None))
        if cmd_attr:
            if isinstance(cmd_attr, (list, tuple, set, frozenset)):
                for c in cmd_attr:
                    PLUGIN_MAP[plugin_key]["cmds"].add(f"/{str(c).lstrip('/')}")
            else:
                PLUGIN_MAP[plugin_key]["cmds"].add(f"/{str(cmd_attr).lstrip('/')}")
        
    return handler

def register_plugin_name(module_name: str):
    """
    允许纯监听类插件（无指令）在 UI 中显示
    """
    plugin_key = module_name.split('.')[-1] if module_name else "未分类"
    if plugin_key not in PLUGIN_MAP:
        module_obj = sys.modules.get(module_name)
        alias = getattr(module_obj, "__MODULE_NAME__", plugin_key.replace('_', ' ').title())
        PLUGIN_MAP[plugin_key] = {
            "alias": alias,
            "file": f"{plugin_key}.py",
            "cmds": {"📡 监听中"} # 默认显示
        }