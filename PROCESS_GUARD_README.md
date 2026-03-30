# BOB 量化模拟盘 - 进程守护与开机自启动

## 📋 概述

进程守护系统确保量化模拟盘的关键服务持续运行，自动重启崩溃的进程，并支持开机自启动。

## 🛡️ 受保护的进程

1. **Web UI** - 网页监控界面 (端口 5000)
2. **BobQuant 主进程** - 模拟盘交易引擎
3. **中频交易** - 中频策略交易程序

## 🚀 快速启动

### 方式 1: 使用进程守护（推荐）

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies

# 前台运行（调试用）
python3 process_guard.py

# 后台运行（生产环境）
python3 process_guard.py --daemon

# 查看状态
python3 process_guard.py --status

# 停止守护
python3 process_guard.py --stop
```

### 方式 2: 使用一键启动脚本

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
./start_all.sh
```

## 🔧 开机自启动（systemd）

### 安装服务

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
sudo ./install_service.sh
```

### 管理命令

```bash
# 启动服务
sudo systemctl start bobquant-quant

# 停止服务
sudo systemctl stop bobquant-quant

# 重启服务
sudo systemctl restart bobquant-quant

# 启用开机自启动
sudo systemctl enable bobquant-quant

# 禁用开机自启动
sudo systemctl disable bobquant-quant

# 查看状态
sudo systemctl status bobquant-quant

# 查看日志
journalctl -u bobquant-quant -f
```

## 📝 日志文件

所有日志位于 `/home/openclaw/.openclaw/workspace/quant_strategies/logs/`:

- `process_guard.log` - 守护进程日志
- `web_ui.log` - Web UI 日志
- `bobquant.log` - 主进程日志
- `medium_frequency_run.log` - 中频交易日志

### 查看日志

```bash
# 实时查看守护日志
tail -f logs/process_guard.log

# 查看最近 100 行
tail -100 logs/process_guard.log

# 查看特定进程日志
tail -f logs/bobquant.log
tail -f logs/medium_frequency_run.log
```

## ⚙️ 配置

### 修改守护进程配置

编辑 `process_guard.py` 中的 `PROCESSES` 列表：

```python
PROCESSES = [
    {
        "name": "进程名称",
        "pattern": "进程匹配关键字",
        "command": "启动命令",
        "log_file": "日志文件路径",
        "enabled": True,  # 是否启用
    },
    # ... 更多进程
]
```

### 修改检查间隔

默认每 30 秒检查一次进程状态。修改 `guard_loop()` 函数中的：

```python
time.sleep(30)  # 修改为其他秒数
```

## 🔍 故障排查

### 进程频繁重启

1. 查看对应日志文件，找出崩溃原因
2. 检查配置文件是否正确
3. 检查端口是否被占用

### 守护进程无法启动

```bash
# 检查是否已运行
python3 process_guard.py --status

# 清理残留 PID 文件
rm logs/process_guard.pid

# 手动启动测试
python3 process_guard.py
```

### systemd 服务问题

```bash
# 检查服务状态
sudo systemctl status bobquant-quant

# 查看详细错误
sudo journalctl -u bobquant-quant -n 50

# 重载配置
sudo systemctl daemon-reload
```

## 📊 监控建议

### 添加系统监控

在 crontab 中添加定期检查：

```bash
crontab -e

# 每 5 分钟检查一次服务状态
*/5 * * * * systemctl is-active --quiet bobquant-quant || sudo systemctl restart bobquant-quant
```

### 资源监控

```bash
# 查看资源占用
ps aux | grep -E "web_ui|bobquant|medium_frequency"

# 查看内存占用
ps aux --sort=-%mem | grep -E "web_ui|bobquant|medium_frequency" | head -10
```

## 🛑 停止服务

### 临时停止

```bash
# 停止守护进程
python3 process_guard.py --stop

# 或停止 systemd 服务
sudo systemctl stop bobquant-quant
```

### 永久禁用

```bash
# 禁用开机自启动
sudo systemctl disable bobquant-quant

# 删除服务
sudo rm /etc/systemd/system/bobquant-quant.service
sudo systemctl daemon-reload
```

## 📞 支持

遇到问题请查看：
1. 日志文件：`logs/*.log`
2. 系统日志：`journalctl -u bobquant-quant`
3. 进程状态：`python3 process_guard.py --status`

---

**最后更新**: 2026-03-30
