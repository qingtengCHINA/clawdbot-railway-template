#!/usr/bin/env python3
"""
OpenClaw 三层记忆系统实现
解决上下文压缩和失忆问题
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import hashlib

class ThreeTierMemory:
    """三层记忆系统"""
    
    def __init__(self, base_path: str = "/data/memory"):
        self.base_path = Path(base_path)
        self.short_term_path = self.base_path / "short-term"
        self.long_term_path = self.base_path / "long-term"
        self.workspace_path = self.base_path / "workspace"
        self.decisions_path = self.long_term_path / "decisions"
        self.embeddings_path = self.base_path / "embeddings"
        
        # 操作计数器（每 2 个操作保存一次）
        self.operation_counter = 0
        self.save_interval = 2
        
        # 心跳时间戳
        self.last_heartbeat = datetime.now()
        self.heartbeat_interval = timedelta(minutes=30)
        
        # 初始化目录结构
        self._init_directories()
        
    def _init_directories(self):
        """初始化目录结构"""
        for path in [
            self.short_term_path,
            self.long_term_path,
            self.workspace_path,
            self.decisions_path,
            self.embeddings_path,
            self.workspace_path / "active_tasks"
        ]:
            path.mkdir(parents=True, exist_ok=True)
        
        # 初始化 NOW.md（最高优先级文件）
        now_file = self.workspace_path / "NOW.md"
        if not now_file.exists():
            self._create_now_file()
    
    def _create_now_file(self):
        """创建初始 NOW.md"""
        template = f"""# 当前状态 - {datetime.now().strftime("%Y-%m-%d %H:%M")}

## 🎯 当前目标
[等待设置目标]

## 📋 活跃任务
无活跃任务

## 🔄 下一步行动
- [ ] 等待用户指令

## 💡 重要上下文
无

## ⚠️ 需要记住的
无

---
*这是最高优先级文件，压缩后优先恢复*
"""
        self._write_file(self.workspace_path / "NOW.md", template)
    
    def _write_file(self, path: Path, content: str):
        """写入文件（原子操作）"""
        path.write_text(content, encoding='utf-8')
    
    def _append_file(self, path: Path, content: str):
        """追加到文件"""
        with open(path, 'a', encoding='utf-8') as f:
            f.write(content + '\n')
    
    def _read_file(self, path: Path) -> str:
        """读取文件"""
        if path.exists():
            return path.read_text(encoding='utf-8')
        return ""
    
    # ==================== 短期记忆 ====================
    
    def save_to_short_term(self, event_type: str, content: str, metadata: Optional[Dict] = None):
        """
        保存到短期记忆（流水账）
        
        Args:
            event_type: 事件类型（conversation, operation, decision, error）
            content: 内容
            metadata: 额外元数据
        """
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = self.short_term_path / f"{today}.md"
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 格式化内容
        entry = f"\n### [{timestamp}] {event_type.upper()}\n"
        entry += f"{content}\n"
        
        if metadata:
            entry += "\n**元数据:**\n"
            for key, value in metadata.items():
                entry += f"- {key}: {value}\n"
        
        entry += "\n---\n"
        
        # 如果文件不存在，先创建头部
        if not file_path.exists():
            header = f"# 短期记忆 - {today}\n\n"
            self._write_file(file_path, header)
        
        # 追加内容
        self._append_file(file_path, entry)
        
        print(f"✅ 已保存到短期记忆: {event_type}")
    
    def get_short_term_summary(self, days: int = 3) -> str:
        """获取最近几天的短期记忆摘要"""
        summaries = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            file_path = self.short_term_path / f"{date}.md"
            
            if file_path.exists():
                content = self._read_file(file_path)
                # 提取关键点（简单实现）
                lines = content.split('\n')
                key_points = [line for line in lines if line.startswith('###')]
                summaries.append(f"\n## {date}\n" + '\n'.join(key_points[:10]))
        
        return '\n'.join(summaries)
    
    # ==================== 长期记忆 ====================
    
    def save_to_long_term(self, category: str, content: str):
        """
        保存到长期记忆（精选提炼）
        
        Args:
            category: 分类（user_info, project_knowledge, patterns, decisions）
            content: 内容
        """
        memory_file = self.long_term_path / "MEMORY.md"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 如果文件不存在，创建模板
        if not memory_file.exists():
            template = f"""# 长期记忆库

## 用户信息
[待补充]

## 项目知识
[待补充]

## 重要决策
[见 decisions/ 目录]

## 常用模式
[待补充]

## 最近更新
- {timestamp}: 初始化长期记忆
"""
            self._write_file(memory_file, template)
        
        # 追加到对应分类
        content_with_timestamp = f"\n### [{timestamp}] {category}\n{content}\n"
        self._append_file(memory_file, content_with_timestamp)
        
        print(f"✅ 已保存到长期记忆: {category}")
    
    def save_decision(self, title: str, content: str, tags: List[str] = None) -> str:
        """
        保存决策锚点（原子化记录）
        
        Returns:
            决策 ID
        """
        # 生成唯一 ID
        decision_id = hashlib.md5(
            f"{title}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]
        
        file_path = self.decisions_path / f"dec_{decision_id}_{title.replace(' ', '_')}.md"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        tags_str = ', '.join(tags) if tags else 'none'
        
        decision_content = f"""# 决策: {title}

**ID:** dec_{decision_id}
**时间:** {timestamp}
**标签:** {tags_str}

## 背景


## 决策内容
{content}

## 理由


## 影响


## 后续行动
- [ ] [待补充]

---
*这是一个决策锚点，压缩后优先搜索*
"""
        
        self._write_file(file_path, decision_content)
        
        # 同时记录到长期记忆索引
        self.save_to_long_term(
            "decisions",
            f"决策 {decision_id}: {title} (参见 decisions/dec_{decision_id}_*.md)"
        )
        
        print(f"✅ 已保存决策锚点: dec_{decision_id}")
        return f"dec_{decision_id}"
    
    # ==================== 工作区记忆 ====================
    
    def update_now(self, 
                   goal: Optional[str] = None,
                   tasks: Optional[List[str]] = None,
                   next_actions: Optional[List[str]] = None,
                   important_context: Optional[List[str]] = None,
                   reminders: Optional[List[str]] = None):
        """
        更新 NOW.md（最高优先级）
        
        这是压缩后第一个恢复的文件
        """
        now_file = self.workspace_path / "NOW.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 读取当前内容以保留未修改的部分
        current = self._read_file(now_file) if now_file.exists() else ""
        
        # 构建新内容
        content = f"# 当前状态 - {timestamp}\n\n"
        
        content += "## 🎯 当前目标\n"
        content += f"{goal or '[未设置]'}\n\n"
        
        content += "## 📋 活跃任务\n"
        if tasks:
            for i, task in enumerate(tasks, 1):
                content += f"{i}. {task}\n"
        else:
            content += "无活跃任务\n"
        content += "\n"
        
        content += "## 🔄 下一步行动\n"
        if next_actions:
            for action in next_actions:
                checked = "x" if action.startswith("[x]") else " "
                action_text = action.replace("[x]", "").replace("[ ]", "").strip()
                content += f"- [{checked}] {action_text}\n"
        else:
            content += "- [ ] 等待用户指令\n"
        content += "\n"
        
        content += "## 💡 重要上下文\n"
        if important_context:
            for ctx in important_context:
                content += f"- {ctx}\n"
        else:
            content += "无\n"
        content += "\n"
        
        content += "## ⚠️ 需要记住的\n"
        if reminders:
            for reminder in reminders:
                content += f"- {reminder}\n"
        else:
            content += "无\n"
        content += "\n"
        
        content += "---\n*这是最高优先级文件，压缩后优先恢复*\n"
        
        self._write_file(now_file, content)
        print("✅ 已更新 NOW.md")
    
    def save_finding(self, finding: str, category: str = "general"):
        """保存发现到 findings.md"""
        findings_file = self.workspace_path / "findings.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        if not findings_file.exists():
            self._write_file(findings_file, "# 发现记录\n\n")
        
        entry = f"\n### [{timestamp}] {category}\n{finding}\n\n"
        self._append_file(findings_file, entry)
        print(f"✅ 已保存发现: {category}")
    
    def update_task_plan(self, task_id: str, plan: str):
        """更新任务计划"""
        task_dir = self.workspace_path / "active_tasks" / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        plan_file = task_dir / "task_plan.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        content = f"""# 任务计划: {task_id}

**更新时间:** {timestamp}

## 计划
{plan}

## 进度
[待更新]

## 笔记
[待添加]
"""
        
        self._write_file(plan_file, content)
        print(f"✅ 已更新任务计划: {task_id}")
    
    # ==================== 操作追踪和自动保存 ====================
    
    def track_operation(self, operation: str, result: str = None):
        """
        追踪操作，每 2 个操作自动保存
        
        Args:
            operation: 操作描述
            result: 操作结果
        """
        self.operation_counter += 1
        
        # 记录到短期记忆
        self.save_to_short_term(
            "operation",
            f"**操作:** {operation}\n**结果:** {result or '执行中'}",
            metadata={"counter": self.operation_counter}
        )
        
        # 每 2 个操作保存一次发现
        if self.operation_counter % self.save_interval == 0:
            self.save_finding(
                f"完成 {self.save_interval} 个操作检查点\n最近操作: {operation}",
                "checkpoint"
            )
            print(f"💾 检查点: 已完成 {self.operation_counter} 个操作")
    
    # ==================== 心跳和维护 ====================
    
    def heartbeat(self):
        """心跳检查（每 30 分钟）"""
        now = datetime.now()
        
        if now - self.last_heartbeat > self.heartbeat_interval:
            print("💓 心跳检查...")
            
            # 检查 NOW.md 是否需要更新
            now_file = self.workspace_path / "NOW.md"
            if now_file.exists():
                mod_time = datetime.fromtimestamp(now_file.stat().st_mtime)
                if now - mod_time > timedelta(hours=2):
                    print("⚠️  NOW.md 超过 2 小时未更新")
            
            # 检查短期记忆文件大小
            today = now.strftime("%Y-%m-%d")
            today_file = self.short_term_path / f"{today}.md"
            if today_file.exists():
                size_kb = today_file.stat().st_size / 1024
                if size_kb > 50:
                    print(f"⚠️  今日短期记忆已达 {size_kb:.1f} KB")
            
            self.last_heartbeat = now
            print("✅ 心跳检查完成")
    
    def compress_old_memories(self, days_to_keep: int = 30):
        """压缩旧的短期记忆到长期记忆"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        compressed_count = 0
        for file_path in self.short_term_path.glob("*.md"):
            try:
                file_date = datetime.strptime(file_path.stem, "%Y-%m-%d")
                if file_date < cutoff_date:
                    # 提取关键点并保存到长期记忆
                    content = self._read_file(file_path)
                    summary = self._extract_key_points(content)
                    
                    self.save_to_long_term(
                        "archived_short_term",
                        f"## {file_path.stem}\n{summary}"
                    )
                    
                    # 删除旧文件
                    file_path.unlink()
                    compressed_count += 1
            except ValueError:
                continue
        
        if compressed_count > 0:
            print(f"🗜️  已压缩 {compressed_count} 个旧的短期记忆文件")
    
    def _extract_key_points(self, content: str, max_points: int = 7) -> str:
        """提取关键点（增量摘要：3-7 条）"""
        # 简单实现：提取所有 ### 标题
        lines = content.split('\n')
        key_lines = [line for line in lines if line.startswith('###')]
        
        # 限制数量
        selected = key_lines[:max_points]
        
        return '\n'.join(selected)
    
    # ==================== 压缩和恢复 ====================
    
    def pre_compression_save(self):
        """
        压缩前的紧急保存
        在检测到上下文即将压缩时调用
        """
        print("🚨 检测到即将压缩，执行紧急保存...")
        
        # 1. 强制更新 NOW.md
        print("1/3 强制保存 NOW.md...")
        # 这里应该从当前上下文提取信息
        # 简化实现：添加时间戳
        now_file = self.workspace_path / "NOW.md"
        content = self._read_file(now_file)
        content += f"\n\n**[压缩前保存 - {datetime.now().strftime('%Y-%m-%d %H:%M')}]**\n"
        self._write_file(now_file, content)
        
        # 2. 生成本次会话摘要（3-7 个关键点）
        print("2/3 生成会话摘要...")
        today = datetime.now().strftime("%Y-%m-%d")
        today_file = self.short_term_path / f"{today}.md"
        if today_file.exists():
            content = self._read_file(today_file)
            summary = self._extract_key_points(content)
            
            summary_file = self.workspace_path / "session_summary.md"
            self._write_file(summary_file, f"# 会话摘要\n\n{summary}")
        
        # 3. 标记重要内容
        print("3/3 标记重要内容...")
        # 这里可以添加更多逻辑
        
        print("✅ 紧急保存完成")
    
    def post_compression_restore(self) -> str:
        """
        压缩后的恢复
        按优先级恢复记忆
        
        Returns:
            恢复的上下文摘要
        """
        print("🔄 开始恢复记忆...")
        
        recovery_context = []
        
        # 优先级 1: NOW.md
        now_file = self.workspace_path / "NOW.md"
        if now_file.exists():
            recovery_context.append("## 当前状态（来自 NOW.md）")
            recovery_context.append(self._read_file(now_file))
            print("✅ 已恢复 NOW.md")
        
        # 优先级 2: 会话摘要
        summary_file = self.workspace_path / "session_summary.md"
        if summary_file.exists():
            recovery_context.append("\n## 最近会话摘要")
            recovery_context.append(self._read_file(summary_file))
            print("✅ 已恢复会话摘要")
        
        # 优先级 3: 最近 3 天短期记忆
        recovery_context.append("\n## 最近活动")
        recovery_context.append(self.get_short_term_summary(days=3))
        print("✅ 已恢复最近短期记忆")
        
        # 优先级 4: 长期记忆核心
        memory_file = self.long_term_path / "MEMORY.md"
        if memory_file.exists():
            recovery_context.append("\n## 长期记忆")
            content = self._read_file(memory_file)
            # 只取前 2000 字符
            recovery_context.append(content[:2000] + "..." if len(content) > 2000 else content)
            print("✅ 已恢复长期记忆")
        
        print("✅ 记忆恢复完成")
        return '\n\n'.join(recovery_context)
    
    # ==================== 语义搜索（简化版）====================
    
    def search_memories(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        搜索记忆（简化版，未使用 embedding）
        
        在实际实现中应该使用 embedding + 向量数据库
        """
        results = []
        
        # 搜索决策文件
        for decision_file in self.decisions_path.glob("dec_*.md"):
            content = self._read_file(decision_file)
            if query.lower() in content.lower():
                results.append({
                    'file': str(decision_file),
                    'type': 'decision',
                    'snippet': content[:200]
                })
        
        # 搜索长期记忆
        memory_file = self.long_term_path / "MEMORY.md"
        if memory_file.exists():
            content = self._read_file(memory_file)
            if query.lower() in content.lower():
                # 找到包含查询的段落
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if query.lower() in line.lower():
                        snippet = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
                        results.append({
                            'file': str(memory_file),
                            'type': 'long_term',
                            'snippet': snippet
                        })
                        break
        
        # 限制结果数量
        return results[:top_k]


# ==================== 使用示例 ====================

def example_usage():
    """示例：如何使用记忆系统"""
    
    memory = ThreeTierMemory()
    
    # 1. 用户发送消息 - 记录到短期记忆
    memory.save_to_short_term(
        "conversation",
        "用户: 帮我分析这个数据集\n我: 好的，我来分析",
        metadata={"user_id": "user123"}
    )
    
    # 2. 更新 NOW.md - 最高优先级
    memory.update_now(
        goal="分析用户提供的数据集",
        tasks=["读取数据", "清洗数据", "生成报告"],
        next_actions=["加载 CSV 文件", "检查缺失值"],
        important_context=["数据集来自客户 ABC", "deadline: 明天"]
    )
    
    # 3. 执行操作并追踪
    memory.track_operation("读取 CSV 文件", "成功读取 1000 行")
    memory.track_operation("数据清洗", "发现 3 个缺失值")
    # 达到 2 个操作，自动保存 checkpoint
    
    # 4. 保存发现
    memory.save_finding(
        "数据集中有 3 个缺失值，集中在 'age' 列",
        category="data_analysis"
    )
    
    # 5. 重要决策 - 保存为锚点
    decision_id = memory.save_decision(
        title="数据清洗策略",
        content="决定使用均值填充缺失的 age 值",
        tags=["data_cleaning", "imputation"]
    )
    
    # 6. 心跳检查
    memory.heartbeat()
    
    # 7. 压缩前保存
    memory.pre_compression_save()
    
    # 8. 压缩后恢复
    context = memory.post_compression_restore()
    print("\n恢复的上下文:")
    print(context)
    
    # 9. 搜索记忆
    results = memory.search_memories("数据清洗")
    print("\n搜索结果:")
    for result in results:
        print(f"- {result['type']}: {result['snippet'][:100]}...")


if __name__ == "__main__":
    example_usage()
