# 基础镜像（slim 减少体积，bullseye 稳定版）
FROM python:3.11-slim-bullseye

# 维护者信息
LABEL maintainer="OpenBot Maintainer <your-email@example.com>"
LABEL version="2.5"
LABEL description="OpenBot - Telegram 插件化下载机器人"

# 设置时区（解决日志/定时任务时区问题）
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装系统依赖（ffmpeg + 基础工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 创建非root用户（提升安全性）
RUN groupadd -r openbot && useradd -r -g openbot openbot

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装（先复制requirements，利用Docker缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip cache purge

# 复制项目代码
COPY . .

# 创建运行时目录并授权
RUN mkdir -p /app/logs /app/sessions /app/download \
    && chown -R openbot:openbot /app

# 切换到非root用户
USER openbot

# 暴露端口（无需端口，仅标识）
EXPOSE 8080

# 启动命令（兼容Windows/Linux EventLoop）
CMD ["python", "main.py"]