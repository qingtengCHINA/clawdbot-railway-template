# Enhanced OpenClaw Railway Template with Pre-installed Tools
# Optimized for GLM-4.7 with maximum capability

FROM node:20-bullseye

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

# 安装系统依赖和工具
RUN apt-get update && apt-get install -y \
    # 基础工具
    curl \
    wget \
    git \
    vim \
    nano \
    unzip \
    zip \
    tar \
    # 格式转换工具（新增，用于修复脚本错误）
    dos2unix \
    # 多媒体处理
    ffmpeg \
    imagemagick \
    libvips-tools \
    # Python 环境
    python3 \
    python3-pip \
    python3-dev \
    # 编译工具
    build-essential \
    g++ \
    make \
    # 网络工具
    net-tools \
    iputils-ping \
    dnsutils \
    # 数据库客户端
    sqlite3 \
    postgresql-client \
    # 其他实用工具
    jq \
    htop \
    tree \
    && rm -rf /var/lib/apt/lists/*

# 升级 pip
RUN pip3 install --upgrade pip setuptools wheel

# 1. 先安装通用 Python 库 (使用默认 PyPI 源)
RUN pip3 install --no-cache-dir \
    requests \
    beautifulsoup4 \
    scrapy \
    selenium \
    pandas \
    numpy \
    openpyxl \
    xlrd \
    pillow \
    opencv-python-headless \
    pydub \
    speechrecognition \
    transformers \
    python-docx \
    pypdf2 \
    markdown \
    python-dotenv \
    pyyaml \
    colorama \
    tqdm \
    click

# 2. 单独安装 PyTorch
RUN pip3 install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 安装 Node.js 全局包
RUN npm install -g \
    sharp \
    jimp \
    axios \
    node-fetch \
    pm2 \
    nodemon \
    fluent-ffmpeg

# 设置工作目录
WORKDIR /app

# 复制 package.json
COPY package*.json ./
RUN npm ci --only=production

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p /data/.openclaw /data/workspace /data/skills /data/tools
RUN chmod -R 755 /data

# 修复并设置脚本权限
# 注意：这里增加了 dos2unix 命令，自动修复 Windows 换行符问题
RUN find scripts -name "*.sh" -exec dos2unix {} \; && \
    chmod +x scripts/*.sh

# 如果根目录下也有 memory_system.py，确保它被复制（COPY . . 已经包含，这里是保险起见）
# 只需要确保 install-memory-system.sh 能被找到

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 启动命令
CMD ["node", "src/index.js"]
