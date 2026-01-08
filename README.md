Telegram-plugin-version-robot 🤖 (V1.0 暴力引擎版)
基于 Python + Telethon + python-telegram-bot 构建的高自由度 Telegram 综合管理机器人，核心采用「MTProto 底层监控层 + Bot API 上层指令交互层」的解耦架构，彻底突破纯 Bot API 机器人的功能限制，支持全量消息监控、高速媒体下载、插件化扩展等核心能力，必须完成 MTProto 账号登录才能解锁全部功能。
🎯 项目核心定位
区别于传统纯 Bot API 机器人仅能响应指令的局限性，本项目将 MTProto 作为核心监控引擎（负责全量消息捕获、底层操作执行），Bot API 作为人机交互入口（负责指令接收、结果反馈），实现 “指令与业务逻辑完全解耦”，让 Telegram 机器人的底层控制力最大化释放。
🏗️ 完整项目架构
整体架构分层
用户

Bot API 层

核心调度层

MTProto 监控层

插件管理层

Telegram 底层消息流

功能插件池

配置管理模块

权限控制模块

任务监控模块

用户

Bot API 层

核心调度层

MTProto 监控层

插件管理层

Telegram 底层消息流

功能插件池

配置管理模块

权限控制模块

任务监控模块


豆包
你的 AI 助手，助力每日工作学习
Bot API 层：仅负责接收用户指令（如 /dl /help）、返回执行结果，无业务逻辑；
核心调度层：作为中间枢纽，解析 Bot API 指令、调度 MTProto 层执行监控 / 下载、管理插件生命周期；
MTProto 监控层：直连 Telegram 底层协议，实现全量消息监听、媒体文件高速下载、频道 / 群组内容搜刮；
插件管理层：负责插件的加载、热更新、禁用，支持第三方插件注入；
基础支撑模块：配置管理、权限控制、任务监控等通用能力，支撑整个框架运行。
📂 详细目录 / 文件说明
目录 / 文件	核心作用	关键子文件 / 说明
core/	项目核心驱动层，承载架构核心逻辑	
├─ core/config.py	全局配置中心	存储 Bot Token、API ID/Hash、路径配置、权限配置等所有核心参数
├─ core/client_manager.py	MTProto/Bot API 客户端生命周期管理	负责 MTProto 会话创建、登录、重连；Bot API 客户端初始化、启停
├─ core/plugin_manager.py	插件管理核心	实现插件注册、热加载、禁用、帮助文档自动扫描等功能
├─ core/task_manager.py	任务监控与调度	管理下载任务、监控任务的生命周期，提供任务状态查询、进度更新
├─ core/permission.py	权限控制模块	实现管理员分级、黑白名单校验、指令权限过滤
features/	官方核心插件目录，所有功能以插件形式存在	
├─ features/basic_cmds.py	基础指令插件	实现 /help /start /status 等通用指令
├─ features/mt_login.py	MTProto 登录插件	实现 /mtlogin 指令，处理手机号验证、Session 持久化
├─ features/downloader.py	核心下载插件	实现 /dl 指令，调用 MTProto 层完成媒体下载、频道搜刮、Album 识别
├─ features/plugin_ops.py	插件操作插件	实现 /add_plugin /disable_plugin /list_plugins 等插件管理指令
├─ features/dashboard.py	可视化看板插件	实现 /dashboard 指令，生成 HTML 格式的实时任务状态看板
sessions/	MTProto 物理会话存储目录	存储 .session 后缀的登录凭证文件，删除后需重新登录
download/	默认媒体 / 文件下载存储目录	按 “频道 / 群组 ID - 时间戳” 自动分目录存储，支持断点续传文件
plugins/	第三方插件目录（可选）	存放用户自定义 / 热安装的插件，需通过 /add_plugin 指令加载
requirements.txt	项目依赖清单	包含 Telethon、python-telegram-bot、requests 等所有依赖包及版本
main.py	项目唯一启动入口	初始化所有核心模块、启动 Bot API 客户端、挂载 MTProto 监控器
Dockerfile	Docker 镜像构建文件	定义 Python 环境、依赖安装、启动命令
docker-compose.yml	Docker 容器编排文件	配置容器挂载目录、环境变量、重启策略
✨ 完整功能清单
1. 核心基础能力
功能分类	具体能力	优势对比（vs 纯 Bot API 机器人）
消息监控	全量监听私聊 / 群组 / 频道的文本、媒体、相册、转发消息	纯 Bot API 仅能监听 @机器人的指令消息，本项目无此限制
账号管理	MTProto Session 持久化登录、多账号切换（扩展）、自动重连	纯 Bot API 仅依赖 Token，无账号级操作能力
权限控制	管理员分级（超级管理员 / 普通管理员）、指令权限过滤、黑白名单	纯 Bot API 需手动开发权限逻辑，本项目内置标准化权限模块
2. 下载核心能力
功能项	具体说明	使用场景
批量媒体下载	自动捕获转发的图片 / 视频 / 文档，批量下载到本地	群组 / 频道内容归档
频道内容搜刮	指定频道 ID，自动遍历并下载频道内所有媒体内容	频道内容批量备份
Album 相册识别	自动识别 Telegram 相册消息，完整下载整套相册（无遗漏）	相册类内容下载
断点续传	大文件下载中断后，重新启动可从断点继续下载	大视频 / 大文件下载
下载速度控制	自定义下载线程数，突破 Bot API 下载限速	高速批量下载
下载过滤	按文件类型（图片 / 视频 / 文档）、大小、关键词过滤下载内容	精准获取目标文件
3. 插件化扩展能力
功能项	具体说明	操作方式
插件热安装	通过 /add_plugin 指令上传插件文件，无需重启机器人即可加载	在线扩展功能
插件禁用 / 启用	通过 /disable_plugin//enable_plugin 指令管理插件状态	灵活控制功能开关
插件帮助文档自动生成	插件内置帮助信息，通过 /help 指令自动汇总所有插件的使用说明	降低使用成本
第三方插件注入	遵循 register(manager) 规范开发的插件，可无缝接入框架	高度自定义扩展
4. 可视化与监控能力
功能项	具体说明	展示形式
实时任务看板	基于 HTML 生成的动态看板，展示下载进度、任务数、磁盘占用	私聊发送 /dashboard 获取
任务状态查询	查询当前运行的下载 / 监控任务，支持任务终止	私聊发送 /status 获取
磁盘空间监控	监控下载目录磁盘占用，超过阈值自动提醒	管理员实时推送
📋 全量指令清单（含使用示例）
一、基础指令（所有用户可访问，部分需管理员权限）
指令	权限要求	功能说明	使用示例
/start	所有用户	启动机器人，返回欢迎语及核心指令指引	/start
/help	所有用户	查看所有插件的帮助文档，汇总全量指令说明	/help
/mtlogin	超级管理员	触发 MTProto 账号登录 / 重新登录（更换账号时使用）	/mtlogin
/status	管理员	查看当前任务状态（下载任务数、监控群组数、磁盘占用）	/status
/dashboard	管理员	获取实时任务看板（HTML 格式）	/dashboard
/version	所有用户	查看机器人当前版本及核心依赖版本	/version
二、下载相关指令
指令	权限要求	功能说明	使用示例
/dl	管理员	启动下载引擎，支持指定频道 / 群组 ID 进行内容搜刮	/dl -c 123456789（搜刮 ID 为 123456789 的频道）
/dl_stop	管理员	终止指定下载任务（无参数终止所有任务）	/dl_stop 1（终止编号为 1 的下载任务）
/dl_filter	超级管理员	设置下载过滤规则（按文件类型 / 大小 / 关键词）	/dl_filter -t video -s 100MB（仅下载大于 100MB 的视频）
/dl_path	超级管理员	修改默认下载目录	/dl_path /data/telegram_download
三、插件管理指令
指令	权限要求	功能说明	使用示例
/add_plugin	超级管理员	热安装插件（需附带插件文件）	发送 /add_plugin + 插件.py 文件
/disable_plugin	超级管理员	禁用指定插件	/disable_plugin downloader
/enable_plugin	超级管理员	启用指定插件	/enable_plugin downloader
/list_plugins	管理员	查看已加载的所有插件及状态（启用 / 禁用）	/list_plugins
四、权限管理指令
指令	权限要求	功能说明	使用示例
/add_admin	超级管理员	添加普通管理员	/add_admin 987654321（添加 ID 为 987654321 的用户为管理员）
/remove_admin	超级管理员	移除普通管理员	/remove_admin 987654321
/add_whitelist	超级管理员	添加用户到白名单（仅白名单用户可使用机器人）	/add_whitelist 987654321
/remove_whitelist	超级管理员	从白名单移除用户	/remove_whitelist 987654321
🛠️ 环境准备与部署
1. 基础环境要求
操作系统：Linux/macOS/Windows（推荐 Linux 服务器部署）
Python 版本：3.11+（3.11.0 兼容性最佳，避免 3.12+ 版本的依赖兼容问题）
依赖工具：pip（Python 包管理工具）、git（克隆项目）、docker/docker-compose（可选，容器部署）
必要凭证：
Telegram Bot Token：从 @BotFather 获取（创建新机器人，输入 /newbot 按指引操作）
Telegram API ID/Hash：从 my.telegram.org 申请（需登录 Telegram 账号，进入 API Development Tools 创建应用）
管理员 ID：从 @userinfobot 获取（发送任意消息，返回的 id 即为管理员 ID）
2. 原生部署步骤（完整流程）
步骤 1：克隆项目
bash
运行
git clone <你的GitHub仓库地址> Telegram-plugin-version-robot
cd Telegram-plugin-version-robot
步骤 2：创建并激活虚拟环境（可选，推荐）
bash
运行
# Linux/macOS
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
步骤 3：安装依赖
bash
运行
pip install -r requirements.txt
步骤 4：配置项目
创建 core/config.py 文件，填入以下内容（替换占位符为实际值）：
python
运行
# core/config.py
# ==================== 基础配置 ====================
# Bot API 配置
BOT_TOKEN = "123456789:ABCdefGhIJKlmNoPQRstUvWxYz123456789"  # 替换为你的Bot Token
# MTProto 配置
API_ID = 1234567  # 替换为你的API ID（数字）
API_HASH = "abcdefghijklmnopqrstuvwxyz1234567890abcd"  # 替换为你的API Hash
# 权限配置
SUPER_ADMIN_IDS = [987654321]  # 超级管理员ID（可填多个，数字列表）
ADMIN_IDS = [123456789]  # 普通管理员ID（可填多个，数字列表）
WHITELIST_ENABLE = True  # 是否启用白名单（True/False）
WHITELIST_IDS = [987654321, 123456789]  # 白名单用户ID

# ==================== 路径配置 ====================
DOWNLOAD_PATH = "./download"  # 默认下载目录
SESSION_PATH = "./sessions"  # MTProto会话存储目录
PLUGIN_PATH = "./features"  # 官方插件目录
THIRD_PARTY_PLUGIN_PATH = "./plugins"  # 第三方插件目录

# ==================== 下载配置 ====================
DL_THREADS = 5  # 下载线程数（越大下载越快，建议5-10）
MAX_FILE_SIZE = 1024 * 1024 * 1024  # 最大下载文件大小（1GB，单位字节）
DL_TIMEOUT = 300  # 下载超时时间（秒）
BREAKPOINT_RESUME = True  # 是否启用断点续传（True/False）

# ==================== 监控配置 ====================
MONITOR_INTERVAL = 1  # 消息监控轮询间隔（秒，越小越实时）
MAX_MONITOR_GROUP = 20  # 最大监控群组/频道数

# ==================== 看板配置 ====================
DASHBOARD_REFRESH_INTERVAL = 5  # 看板刷新间隔（秒）
DISK_WARNING_THRESHOLD = 80  # 磁盘占用警告阈值（%）
步骤 5：启动机器人
bash
运行
python main.py
步骤 6：完成 MTProto 登录（必做）
启动后终端会提示输入信息，按以下步骤操作：
输入 Telegram 手机号（带国家码，如 +8613800138000）；
输入收到的验证码（手机 / 电报客户端会收到 5-6 位数字验证码）；
若账号开启两步验证，输入两步验证密码；
登录成功后，终端提示 “MTProto 登录成功”，sessions/ 目录会生成 .session 后缀的会话文件；
此时 Bot API 客户端也会启动，机器人进入运行状态，可在 Telegram 私聊机器人发送 /start 验证。
3. Docker 容器部署（推荐生产环境）
步骤 1：编写 Dockerfile
在项目根目录创建 Dockerfile：
dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . /app

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要目录
RUN mkdir -p /app/download /app/sessions /app/plugins

# 启动命令
CMD ["python", "main.py"]
步骤 2：编写 docker-compose.yml
在项目根目录创建 docker-compose.yml：
yaml
version: '3.8'

services:
  telegram-robot:
    build: .
    container_name: telegram-robot
    restart: always
    environment:
      - BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstUvWxYz123456789  # 替换为你的Bot Token
      - API_ID=1234567  # 替换为你的API ID
      - API_HASH=abcdefghijklmnopqrstuvwxyz1234567890abcd  # 替换为你的API Hash
      - SUPER_ADMIN_IDS=987654321  # 替换为你的超级管理员ID
    volumes:
      - ./download:/app/download  # 持久化下载文件
      - ./sessions:/app/sessions  # 持久化会话文件
      - ./plugins:/app/plugins    # 持久化第三方插件
    networks:
      - telegram-robot-network

networks:
  telegram-robot-network:
    driver: bridge
步骤 3：启动容器
bash
运行
# 构建并启动容器
docker-compose up -d --build

# 查看容器日志（确认启动/登录状态）
docker-compose logs -f telegram-robot
步骤 4：容器内完成 MTProto 登录
bash
运行
# 进入容器
docker exec -it telegram-robot /bin/bash

# 启动机器人并完成登录（若未自动触发）
python main.py
⚠️ 核心注意事项
会话文件保护：sessions/ 目录下的 .session 文件是 MTProto 登录凭证，泄露会导致账号被盗，需严格权限控制（Linux 下可设置 chmod 600 sessions/*）；
频率限制规避：
避免短时间内监控大量频道 / 群组（建议单机器人监控≤20 个）；
下载线程数建议 5-10，过高易触发 Telegram 限流；
批量下载时建议设置间隔，避免单次请求过多；
依赖兼容：Python 3.12+ 版本可能导致 Telethon 部分功能异常，优先使用 3.11.x 版本；
磁盘空间管理：下载大量媒体文件前需确认磁盘空间，建议开启磁盘监控阈值提醒；
权限控制：生产环境建议启用白名单（WHITELIST_ENABLE = True），仅允许指定用户使用机器人，避免滥用；
重启与更新：
原生部署重启：终止进程后重新执行 python main.py 即可（会话文件存在无需重新登录）；
插件更新：热安装插件无需重启，修改核心代码需重启机器人；
Docker 部署更新：docker-compose down → 拉取最新代码 → docker-compose up -d --build。
📄 许可证
本项目采用 MIT 开源许可证，你可以自由使用、修改、分发本项目，商用需保留原作者版权声明。
📞 问题反馈
若使用过程中遇到问题，可通过以下方式反馈：
在 GitHub 仓库提交 Issue；
联系超级管理员 ID（配置文件中 SUPER_ADMIN_IDS 中的账号）。
