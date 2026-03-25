# 多 OpenClaw 实例协作方案

## 架构设计

```
┌─────────────────┐         ┌─────────────────┐
│  Ubuntu A       │         │  Ubuntu B       │
│  OpenClaw-1     │◄───────►│  OpenClaw-2     │
│                 │         │                 │
│  - 协调者       │  通信   │  - 执行者       │
│  - 任务分解     │  通道   │  - 具体执行     │
│  - 结果整合     │         │  - 技能学习     │
└─────────────────┘         └─────────────────┘
         │                           │
         └───────────┬───────────────┘
                     │
         ┌───────────▼───────────────┐
         │    共享工作区 (Git/NFS)    │
         │    - skills/              │
         │    - memory/              │
         │    - TOOLS.md             │
         └───────────────────────────┘
```

## 通信方案

### 方案 1: 飞书消息（推荐）

两个实例配置不同的飞书应用或机器人，通过群聊通信：

**配置步骤：**
1. 创建飞书群 "OpenClaw 协作组"
2. 两个实例都加入群聊
3. 使用特定前缀标识消息来源：
   - `[OC-A]` = OpenClaw A 发送
   - `[OC-B]` = OpenClaw B 发送

**消息格式示例：**
```json
{
  "from": "OC-A",
  "task_id": "task-001",
  "action": "request",
  "content": "请搜索 Python 异步编程最佳实践",
  "priority": "normal"
}
```

### 方案 2: HTTP API

在每个实例上运行轻量 API 服务：

**server.py (两个实例都部署):**
```python
from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route('/task', methods=['POST'])
def receive_task():
    data = request.json
    # 将任务写入待处理队列
    with open('/tmp/openclaw_tasks.jsonl', 'a') as f:
        f.write(json.dumps(data) + '\n')
    return jsonify({'status': 'received'})

@app.route('/status', methods=['GET'])
def status():
    return jsonify({'status': 'online', 'instance': 'OC-A'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

**调用示例：**
```bash
# A 发送任务给 B
curl -X POST http://ubuntu-b-ip:5000/task \
  -H "Content-Type: application/json" \
  -d '{"task": "搜索最新 AI 新闻", "priority": "high"}'
```

## 技能同步方案

### 方案 1: Git 同步（推荐）

**初始化共享仓库：**
```bash
# 在 Ubuntu A 上
cd ~/.openclaw/workspace
git init
git remote add origin git@github.com:youruser/openclaw-shared.git
git add skills/ memory/ TOOLS.md
git commit -m "Initial shared workspace"
git push -u origin main

# 在 Ubuntu B 上
cd ~/.openclaw/workspace
git clone git@github.com:youruser/openclaw-shared.git .
```

**自动同步脚本 (sync-skills.sh):**
```bash
#!/bin/bash
# 添加到 cron，每 5 分钟同步一次

cd ~/.openclaw/workspace
git pull origin main

# 如果有新技能，重新加载
if git diff --name-only HEAD@{1} HEAD | grep -q "skills/"; then
    echo "检测到新技能，重新加载中..."
    # 触发 OpenClaw 重新加载技能
    # 可以通过 gateway restart 或特定信号
fi
```

### 方案 2: Syncthing 实时同步

**配置步骤：**
```bash
# 两个 Ubuntu 都安装
sudo apt install syncthing

# 启动并配置 Web 界面
syncthing &
# 访问 http://localhost:8384

# 互相添加设备 ID
# 共享 ~/.openclaw/workspace/skills 和 memory 目录
```

## 协作任务示例

### 示例 1: 分布式搜索

```
OpenClaw-A: 接收用户请求 "研究 Rust 和 Go 的性能对比"
    ↓ 分解任务
    ├─→ 自己搜索：Rust 性能特点
    └─→ 发送请求给 B：请搜索 Go 性能特点
            ↓
OpenClaw-B: 接收请求
    ↓ 执行搜索
    ↓ 返回结果给 A
            ↓
OpenClaw-A: 整合两个结果
    ↓ 生成对比报告
    ↓ 回复用户
```

### 示例 2: 互相学习技能

```
OpenClaw-A: 发现新技能需求
    ↓ 创建技能文件 skills/new-skill/SKILL.md
    ↓ git commit & push
    ↓ 通知 B 有新技能
            ↓
OpenClaw-B: 收到通知
    ↓ git pull
    ↓ 读取新 SKILL.md
    ↓ 技能生效
    ↓ 确认 A：技能已加载
```

### 示例 3: 互相评审

```
OpenClaw-A: 生成代码解决方案
    ↓ 发送请求给 B：请评审这段代码
            ↓
OpenClaw-B: 接收代码
    ↓ 分析代码质量、安全性、性能
    ↓ 返回评审意见
            ↓
OpenClaw-A: 根据评审优化代码
    ↓ 输出最终方案
```

## 心跳与状态同步

创建 `HEARTBEAT.md` 定期检查协作状态：

```markdown
# HEARTBEAT.md

- [ ] 检查另一个 OpenClaw 实例是否在线
- [ ] 同步共享工作区 (git pull)
- [ ] 检查有待处理的任务请求
- [ ] 报告当前负载状态
```

## 安全考虑

1. **网络隔离**: 两个实例间通信使用内网 IP
2. **认证机制**: HTTP API 添加 token 验证
3. **任务验证**: 不执行来自另一个实例的危险命令
4. **速率限制**: 避免互相发送过多请求造成循环

## 启动脚本示例

**start-collaboration.sh:**
```bash
#!/bin/bash

# 启动 OpenClaw
openclaw gateway start &

# 启动 HTTP API (如果使用方案 2)
python3 /home/openclaw/.openclaw/workspace/scripts/collab-server.py &

# 启动同步服务
/home/openclaw/.openclaw/workspace/scripts/sync-skills.sh &

echo "OpenClaw 协作节点已启动"
```

## 下一步

1. 选择通信方案（推荐飞书消息）
2. 配置共享工作区（推荐 Git）
3. 编写协作协议文档
4. 测试基本通信
5. 实现任务分配逻辑
