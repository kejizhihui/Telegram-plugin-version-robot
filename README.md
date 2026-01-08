Telegram-plugin-version-robot 🤖 (V1.0 暴力引擎版)
基于 Python + Telethon + python-telegram-bot 构建的插件化 Telegram 综合管理框架，核心采用「MTProto 监控层 + Bot API 指令交互层」双引擎架构，彻底摆脱纯 Bot API 架构的功能束缚，让 MTProto 底层控制力最大化释放（必须完成 MTProto 登录后才能解锁完整功能）。
🎯 核心架构优势（对比纯 Bot API 架构）
架构维度	纯 Bot API 架构	本项目「MTProto+Bot API」架构
消息监控范围	仅能捕获带 / 前缀的指令消息	全量监听私聊 / 群组 / 频道的所有消息（文本 / 媒体 / 相册）
逻辑耦合度	指令与业务逻辑强绑定	指令交互与监控业务完全解耦，扩展更灵活
底层控制力	受 Bot API 接口限制（如下载限速）	直连 Telegram 底层 MTProto 协议，暴力下载 / 实时监控
登录依赖	仅需 Bot Token	Session 持久化登录，免密复用，功能完整解锁
🌟 核心特性
🚀 双引擎分工明确：MTProto 作为核心监控层（全量消息捕获 / 暴力下载），Bot API 作为指令交互层（用户指令接收 / 结果反馈），逻辑无黏连；
⚡ MT-Downloader 暴力秒下：支持频道内容搜刮、Album 自动识别、批量媒体下载、断点续传，下载速度远超 Bot API 限制；
🔌 插件化架构 V2.5：register(manager) 注入式结构，/add_plugin 指令实现热安装，免重启部署新功能；
📊 可视化看板 UI：基于 HTML 解析的实时任务状态滚动更新，支持下载进度 / 磁盘监控 / 任务统计；
🛡️ 精细化权限管控：管理员权限分级、黑白名单扩展，适配私有化部署；
📝 自动化文档：自动扫描插件帮助文档，生成统一 /help 菜单；
🐳 容器化部署：Docker / Docker-Compose 一键部署，目录持久化不丢失数据。
📂 目录结构
plaintext
Telegram-plugin-version-robot/
├── core/               # 核心驱动层（配置管理/客户端生命周期/统一注册表）
├── features/           # 官方插件层（基础指令/下载引擎/管理员功能）
├── sessions/           # MTProto 物理会话存储（持久化登录凭证）
├── download/           # 默认文件存储路径（下载的媒体/文件）
├── requirements.txt    # 项目依赖清单
└── main.py             # 项目启动入口
🛠️ 环境准备
基础要求
Python 3.11+（推荐 3.11.0，兼容性最佳）
Telegram Bot Token（从 @BotFather 获取）
Telegram API ID/Hash（从 my.telegram.org 申请）
管理员 ID（从 @userinfobot 获取）
🚀 快速开始（原生部署）
步骤 1：克隆项目
bash
运行
git clone <你的GitHub仓库地址> Telegram-plugin-version-robot
cd Telegram-plugin-version-robot
步骤 2：安装依赖
bash
运行
pip install -r requirements.txt
步骤 3：配置项目
复制并修改配置文件（建议在 core/ 目录下创建 config.py）：
python
运行
# core/config.py
# 基础配置
BOT_TOKEN = "你的Bot Token"
API_ID = 你的API ID（数字）
API_HASH = "你的API Hash"
ADMIN_IDS = [你的管理员ID（数字）]  # 支持多个管理员

# 下载配置
DOWNLOAD_PATH = "./download"
SESSION_PATH = "./sessions"

# 插件配置
PLUGIN_PATH = "./features"
步骤 4：启动项目
bash
运行
python main.py
步骤 5：完成 MTProto 登录（必做）
启动后，在终端按照提示输入 Telegram 手机号（带国家码，如 +86138xxxxxxx）；
输入收到的验证码，完成 MTProto Session 登录；
登录成功后，Session 文件会自动保存到 sessions/ 目录，后续启动无需重复登录。
📌 核心功能使用
1. 基础指令（Bot API 交互层）
指令	功能说明
/help	查看所有插件的帮助文档
/mtlogin	重新触发 MTProto 登录（如需更换账号）
/dl	启动 MTProto 下载引擎，监控指定频道 / 群组
/add_plugin	热安装新插件（传入插件文件路径）
/status	查看当前任务状态（下载 / 监控）
2. MTProto 监控层核心能力
自动捕获转发给机器人的所有媒体消息，触发批量下载；
监控指定群组 / 频道的新消息，自动搜刮媒体内容；
识别 Album 类型消息，完整下载整套相册；
跳过 Bot API 硬控限制，直接调用底层接口实现高速下载。
🐳 Docker 部署（可选）
bash
运行
# 构建镜像
docker build -t telegram-robot:v1.0 .

# 启动容器（持久化会话和下载目录）
docker run -d \
  --name telegram-robot \
  -v $(pwd)/sessions:/app/sessions \
  -v $(pwd)/download:/app/download \
  -e BOT_TOKEN="你的Bot Token" \
  -e API_ID=你的API ID \
  -e API_HASH="你的API Hash" \
  telegram-robot:v1.0
⚠️ 注意事项
确保 API ID/Hash 与登录手机号对应，否则会导致 MTProto 登录失败；
下载大文件时，建议预留足够的磁盘空间，默认存储路径为 download/；
避免高频监控大量频道 / 群组，防止触发 Telegram 限流机制；
sessions/ 目录存储 MTProto 登录凭证，请勿泄露或删除，否则需重新登录。
