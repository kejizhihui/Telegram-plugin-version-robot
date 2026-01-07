#openbot\core\config_manager.py
import os
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, env_path: str = ".env"):
        self.env_path = env_path
        # 初始化配置字典（从.env读取）
        self.config = self._load_env()

    def _load_env(self) -> dict:
        """内置方法读取.env文件，不依赖第三方库"""
        config = {}
        # 如果.env文件不存在，创建空文件
        if not os.path.exists(self.env_path):
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.write("")
            return config
        
        # 逐行读取.env，解析键值对
        with open(self.env_path, "r", encoding="utf-8") as f:
            for line in f.readlines():
                line = line.strip()
                # 跳过注释和空行
                if not line or line.startswith("#"):
                    continue
                # 解析 KEY=VALUE 格式
                if "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
        
        # 同步到系统环境变量
        for k, v in config.items():
            os.environ[k] = v
        return config

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """获取配置项（优先系统环境变量，其次.env）"""
        return os.getenv(key, self.config.get(key, default))
    
    def set(self, key: str, value: str) -> None:
        """设置配置项并写入.env（修复换行贴合问题）"""
        self.config[key] = value
        os.environ[key] = value

        lines = []
        if os.path.exists(self.env_path):
            with open(self.env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        new_lines = []
        key_found = False
        
        for line in lines:
            line_strip = line.strip()
            # 保持空行和注释
            if not line_strip or line_strip.startswith("#"):
                new_lines.append(line)
                continue
            
            # 找到现有的 key 则替换
            if line_strip.startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                key_found = True
            else:
                new_lines.append(line)
        
        # 如果是新 key，执行追加逻辑
        if not key_found:
            # 【核心修复】如果最后一行缺换行符，先补一个
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] = new_lines[-1] + "\n"
            
            new_lines.append(f"{key}={value}\n")
        
        # 写入文件
        with open(self.env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        
        logger.info(f"Config updated: {key} = {value[:20]}...")