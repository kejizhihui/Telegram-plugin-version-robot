# Telegram-plugin-version-robot
这版本是MTProto监听Bot API控制命令！！！！

# 🚀 OpenBot 2026 (V2.5 暴力引擎版)

基于 **Bot API** 与 **MTProto** 双引擎构建的 Telegram 综合管理框架。

## 🌟 核心特性
- **双引擎对齐**: 结合了 Bot API 的易用性与 MTProto 的底层控制力。
- **MT-Downloader**: 暴力秒下引擎，支持频道搜刮、Album 自动识别及监控同步。
- **插件化架构**: 采用 V2.5 `register(manager)` 注入式结构，解耦业务逻辑。
- **热安装模式**: `/add_plugin` 指令实现免重启动态部署新功能。
- **看板 UI**: 基于 HTML 解析的实时任务状态滚动更新。

## 📂 目录结构
- `core/`: 核心驱动层（配置管理、客户端生命周期、统一注册表）。
- `features/`: 官方插件层（基础指令、下载引擎、管理员功能）。
- `sessions/`: 存储 MTProto 物理会话。
- `download/`: 默认文件存储路径。

## 🛠️ 快速开始

1. **安装依赖**:
   ```bash
   pip install -r requirements.txt


# OpenBot 🤖
一款基于 Python + Telethon + python-telegram-bot 构建的**插件化 Telegram 下载机器人**，支持 MTProto 协议、自动插件加载、批量媒体下载、权限管控，适配私有化部署。

## ✨ 核心特性
- 🚀 **双协议引擎**：Bot API（指令交互）+ MTProto（下载/登录），Session 持久化免密登录
- 📥 **智能下载**：自动捕获转发媒体、批量频道搜刮、关键词过滤、断点续传
- 🔌 **插件化架构**：热加载/禁用插件、在线安装新插件，无需重启程序
- 🛡️ **权限管控**：精细化管理员权限，支持黑白名单（扩展）
- 📊 **可视化看板**：下载进度实时展示、任务统计、磁盘监控
- 📝 **自动化文档**：自动扫描插件帮助文档，生成统一 /help 菜单
- 🐳 **容器化部署**：Docker / Docker-Compose 一键部署，目录持久化

## 📋 环境准备
### 1. 基础要求
- Python 3.11+（推荐3.11.0，与项目兼容）
- Telegram Bot Token（[@BotFather](https://t.me/BotFather) 获取）
- Telegram API ID/Hash（[my.telegram.org](https://my.telegram.org) 获取）
- 管理员 ID（[@userinfobot](https://t.me/userinfobot) 获取）

### 2. 快速开始（原生部署）
#### 步骤1：克隆项目
```bash
git clone <your-repo-url> openbot
cd openbot
