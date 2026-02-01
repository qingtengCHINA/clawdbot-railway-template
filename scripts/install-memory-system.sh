#!/bin/bash

# OpenClaw 记忆系统安装和集成脚本

set -e

echo "🧠 安装 OpenClaw 记忆系统..."

# 创建记忆目录结构
echo "📁 创建目录结构..."
mkdir -p /data/memory/short-term
mkdir -p /data/memory/long-term/decisions
mkdir -p /data/memory/long-term/summaries
mkdir -p /data/memory/workspace/active_tasks
mkdir -p /data/memory/embeddings

# 复制记忆系统脚本
echo "📋 安装记忆系统脚本..."
cp /app/memory_system.py /data/memory/
chmod +x /data/memory/memory_system.py

# 安装 Python 依赖（如果需要语义搜索）
echo "📦 安装依赖..."
pip3 install --no-cache-dir --break-system-packages \
    sentence-transformers \
    faiss-cpu \
    2>/dev/null || echo "⚠️  部分依赖安装失败，将使用基础搜索"

# 创建记忆系统配置
echo "⚙️  创建配置文件..."
cat > /data/memory/config.json <<'EOF'
{
  "version": "1.0.0",
  "system": "three-tier",
  "paths": {
    "base": "/data/memory",
    "shortTerm": "/data/memory/short-term",
    "longTerm": "/data/memory/long-term",
    "workspace": "/data/memory/workspace"
  },
  "automation": {
    "autoSave": true,
    "saveInterval": 2,
    "heartbeatMinutes": 30,
    "compression": {
      "enabled": true,
      "shortTermRetentionDays": 30
    }
  },
  "priority": {
    "nowFile": "workspace/NOW.md",
    "recoveryOrder": [
      "workspace/NOW.md",
      "workspace/session_summary.md",
      "workspace/task_plan.md",
      "short-term/recent-summary.md",
      "long-term/MEMORY.md"
    ]
  },
  "search": {
    "enabled": true,
    "method": "keyword",
    "topK": 5
  }
}
EOF

# 创建记忆系统集成的 OpenClaw 配置片段
echo "🔧 生成 OpenClaw 配置..."
cat > /data/memory/openclaw-memory-config.json <<'EOF'
{
  "memory": {
    "enabled": true,
    "system": "three-tier",
    "paths": {
      "base": "/data/memory",
      "shortTerm": "/data/memory/short-term",
      "longTerm": "/data/memory/long-term",
      "workspace": "/data/memory/workspace"
    },
    "automation": {
      "autoSave": true,
      "saveInterval": 2,
      "heartbeat": 1800
    },
    "hooks": {
      "beforeCompression": "python3 /data/memory/memory_system.py pre_compression",
      "afterCompression": "python3 /data/memory/memory_system.py post_compression",
      "onMessage": "python3 /data/memory/memory_system.py on_message",
      "onOperation": "python3 /data/memory/memory_system.py on_operation"
    }
  }
}
EOF

# 创建系统提示词增强（告诉 AI 如何使用记忆系统）
echo "📝 创建增强系统提示词..."
cat > /data/memory/memory-enhanced-prompt.txt <<'EOF'
# 记忆系统使用指南

你现在拥有一个三层记忆系统来对抗上下文压缩和失忆：

## 核心原则："Mental notes are lies"
**永远不要依赖记忆！立即写入文件！**

## 三层记忆

### 1. 短期记忆（流水账）
- 位置: /data/memory/short-term/YYYY-MM-DD.md
- 用途: 记录所有发生的事
- 何时写: 每次对话、每次操作

### 2. 长期记忆（提炼）
- 位置: /data/memory/long-term/MEMORY.md
- 用途: 精选的重点知识
- 何时写: 学到重要经验、做出关键决策

### 3. 工作区记忆（任务）
- NOW.md: **最高优先级**，压缩后第一个恢复
- task_plan.md: 任务计划
- findings.md: 发现记录

## 关键文件：NOW.md

这是你的生命线！**每次重要变化都要更新！**

必须包含：
- 🎯 当前目标
- 📋 活跃任务
- 🔄 下一步行动
- 💡 重要上下文
- ⚠️ 需要记住的

## 自动保存规则

**每 2 个操作自动保存一次**

示例：
```
操作 1: 读取文件
操作 2: 分析数据
→ 自动保存到 findings.md

操作 3: 生成报告
操作 4: 优化代码
→ 再次自动保存
```

## 重要决策要原子化

不要把决策混在对话里！创建独立文件：

```python
memory.save_decision(
    title="选择数据库方案",
    content="决定使用 PostgreSQL 而非 MongoDB，因为...",
    tags=["architecture", "database"]
)
```

## 压缩前/后行为

### 检测到即将压缩时：
1. 立即更新 NOW.md
2. 生成 3-7 条关键摘要
3. 标记重要决策

### 压缩后恢复时：
1. 首先读取 NOW.md
2. 读取会话摘要
3. 搜索相关决策锚点
4. 继续工作

## 实际使用示例

### 场景 1: 用户请求分析数据
```
1. [立即] 写入短期记忆: 用户请求分析数据集 XYZ
2. [立即] 更新 NOW.md: 目标=分析数据集 XYZ
3. [执行] 读取数据
4. [执行] 分析数据
5. [自动] 保存 checkpoint（2 个操作）
6. [发现] 保存到 findings.md: 发现 3 个异常值
7. [完成] 更新 NOW.md: 下一步=生成报告
```

### 场景 2: 重要技术决策
```
1. [思考] 需要选择数据库
2. [立即] 创建决策锚点: dec_001_database_choice.md
3. [记录] 在决策文件中详细说明理由
4. [索引] 保存到长期记忆索引
5. [更新] NOW.md: 已完成数据库选型
```

### 场景 3: 长对话即将压缩
```
1. [检测] 上下文接近限制
2. [紧急] 强制更新 NOW.md 保存当前状态
3. [摘要] 提取本次会话 3-7 个关键点
4. [准备] 创建恢复优先级队列
5. [压缩] 让系统压缩
6. [恢复] 从 NOW.md 开始恢复
7. [继续] 基于恢复的上下文继续工作
```

## 命令快捷方式

你可以使用以下 Python 代码操作记忆系统：

```python
from memory_system import ThreeTierMemory

memory = ThreeTierMemory()

# 保存到短期记忆
memory.save_to_short_term("conversation", "用户问了...")

# 更新 NOW.md（最重要！）
memory.update_now(
    goal="当前目标",
    tasks=["任务1", "任务2"],
    next_actions=["下一步1", "下一步2"]
)

# 保存发现
memory.save_finding("发现了一个bug", "debugging")

# 保存决策
memory.save_decision("架构选择", "我们决定...", ["architecture"])

# 追踪操作（自动 checkpoint）
memory.track_operation("读取文件", "成功")

# 搜索记忆
results = memory.search_memories("数据库")
```

## ⚠️ 绝对不要做的事

❌ "我会记住这个" - 不，你不会！写文件！
❌ "我刚才说过..." - 不要依赖上下文！读 NOW.md！
❌ 把重要信息只放在对话里 - 立即写入记忆系统！
❌ 等到"稍后"再保存 - 现在就保存！

## ✅ 永远要做的事

✅ 每次重要变化立即更新 NOW.md
✅ 每 2 个操作保存 checkpoint
✅ 重要决策创建独立文件
✅ 压缩前紧急保存状态
✅ 压缩后从 NOW.md 恢复

---

**记住：这个系统存在的唯一原因就是你会失忆！主动使用它！**
EOF

# 创建便捷的命令行工具
echo "🛠️  创建命令行工具..."
cat > /data/memory/memory-cli.sh <<'EOF'
#!/bin/bash
# 记忆系统命令行工具

case "$1" in
    status)
        echo "📊 记忆系统状态:"
        echo "短期记忆文件: $(ls /data/memory/short-term | wc -l)"
        echo "决策锚点: $(ls /data/memory/long-term/decisions | wc -l)"
        echo "活跃任务: $(ls /data/memory/workspace/active_tasks | wc -l)"
        ;;
    show-now)
        echo "📄 NOW.md 内容:"
        cat /data/memory/workspace/NOW.md
        ;;
    heartbeat)
        echo "💓 执行心跳检查..."
        python3 /data/memory/memory_system.py heartbeat
        ;;
    compress)
        echo "🗜️  压缩旧记忆..."
        python3 /data/memory/memory_system.py compress
        ;;
    search)
        echo "🔍 搜索记忆: $2"
        python3 /data/memory/memory_system.py search "$2"
        ;;
    *)
        echo "用法: $0 {status|show-now|heartbeat|compress|search <query>}"
        exit 1
        ;;
esac
EOF

chmod +x /data/memory/memory-cli.sh

# 创建定时任务配置（cron）
echo "⏰ 配置定时任务..."
cat > /data/memory/crontab.txt <<'EOF'
# OpenClaw 记忆系统定时任务

# 每 30 分钟执行心跳检查
*/30 * * * * /data/memory/memory-cli.sh heartbeat

# 每天凌晨 2 点压缩旧记忆
0 2 * * * /data/memory/memory-cli.sh compress

# 每周日凌晨 3 点完整备份
0 3 * * 0 tar -czf /data/memory/backups/memory-$(date +\%Y\%m\%d).tar.gz /data/memory/
EOF

# 创建备份目录
mkdir -p /data/memory/backups

# 初始化 NOW.md
echo "📝 初始化 NOW.md..."
python3 /data/memory/memory_system.py init

echo ""
echo "✅ 记忆系统安装完成！"
echo ""
echo "📁 目录结构:"
echo "  - /data/memory/short-term/     (短期记忆)"
echo "  - /data/memory/long-term/      (长期记忆)"
echo "  - /data/memory/workspace/      (工作区)"
echo "  - /data/memory/workspace/NOW.md (最高优先级文件)"
echo ""
echo "🛠️  命令行工具:"
echo "  /data/memory/memory-cli.sh status    (查看状态)"
echo "  /data/memory/memory-cli.sh show-now  (显示 NOW.md)"
echo "  /data/memory/memory-cli.sh heartbeat (心跳检查)"
echo "  /data/memory/memory-cli.sh compress  (压缩旧记忆)"
echo "  /data/memory/memory-cli.sh search <query> (搜索记忆)"
echo ""
echo "📚 文档:"
echo "  /data/memory/memory-enhanced-prompt.txt (系统提示词)"
echo "  /data/memory/config.json (配置文件)"
echo ""
echo "🎯 下一步:"
echo "  1. 将 memory-enhanced-prompt.txt 的内容添加到你的系统提示词"
echo "  2. 将 openclaw-memory-config.json 合并到 OpenClaw 配置"
echo "  3. 测试: /data/memory/memory-cli.sh status"
echo ""
EOF

chmod +x /data/memory/install-memory-system.sh

echo "✅ 安装脚本创建完成"
