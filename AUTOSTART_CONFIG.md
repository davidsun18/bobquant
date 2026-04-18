# BobQuant 开机自启动配置

**配置日期**: 2026-04-18  
**配置方式**: systemd user services

---

## ✅ 已配置服务

| 服务名 | 说明 | 状态 | 开机自启 |
|--------|------|------|----------|
| `openclaw-gateway.service` | OpenClaw 网关 | ✅ enabled | ✅ |
| `bobquant-dashboard.service` | Web UI Dashboard | ✅ enabled | ✅ |
| `bobquant-execution.service` | Execution Bot (模拟交易) | ✅ enabled | ✅ |
| `bobquant-data-collector.service` | Data Bot (数据采集) | ✅ enabled | ✅ |
| `bob-quant-guard.service` | 进程守护 | ✅ enabled | ✅ |

---

## 📁 服务文件位置

```
/home/openclaw/.config/systemd/user/
├── openclaw-gateway.service          # OpenClaw 网关
├── bobquant-dashboard.service        # Dashboard Web UI
├── bobquant-execution.service        # Execution Bot
├── bobquant-data-collector.service   # Data Collector
└── bob-quant-guard.service           # 进程守护
```

---

## 🔧 服务配置详情

### 1. Dashboard 服务

**文件**: `~/.config/systemd/user/bobquant-dashboard.service`

```ini
[Unit]
Description=BobQuant Dashboard (FastAPI Web UI)
After=network.target openclaw-gateway.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/openclaw/.openclaw/workspace/dashboard/main.py
WorkingDirectory=/home/openclaw/.openclaw/workspace/dashboard
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

**访问地址**: http://localhost:8500/dashboard

---

### 2. Execution Bot 服务

**文件**: `~/.config/systemd/user/bobquant-execution.service`

```ini
[Unit]
Description=BobQuant Execution Bot (模拟交易)
After=network.target openclaw-gateway.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/openclaw/.openclaw/workspace/agents/execution_bot/main.py
WorkingDirectory=/home/openclaw/.openclaw/workspace/agents/execution_bot
Restart=always

[Install]
WantedBy=default.target
```

---

### 3. Data Collector 服务

**文件**: `~/.config/systemd/user/bobquant-data-collector.service`

```ini
[Unit]
Description=BobQuant Data Collector (数据采集)
After=network.target openclaw-gateway.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/openclaw/.openclaw/workspace/agents/data-bot/scripts/collect_data.py
WorkingDirectory=/home/openclaw/.openclaw/workspace/agents/data-bot/scripts
Restart=always
RestartSec=300  # 5 分钟重试

[Install]
WantedBy=default.target
```

---

## 🚀 管理命令

### 查看所有服务状态
```bash
systemctl --user list-unit-files --type=service | grep bobquant
```

### 查看单个服务状态
```bash
systemctl --user status bobquant-dashboard.service
```

### 启动/停止/重启服务
```bash
systemctl --user start bobquant-dashboard.service
systemctl --user stop bobquant-dashboard.service
systemctl --user restart bobquant-dashboard.service
```

### 禁用开机自启
```bash
systemctl --user disable bobquant-dashboard.service
```

### 查看服务日志
```bash
journalctl --user -u bobquant-dashboard.service -f
```

---

## ✅ 验证步骤

### 1. 检查服务是否启用
```bash
systemctl --user list-unit-files --type=service | grep enabled
```

**预期输出**:
```
bobquant-dashboard.service                                        enabled
bobquant-execution.service                                        enabled
bobquant-data-collector.service                                   enabled
openclaw-gateway.service                                          enabled
```

### 2. 检查服务是否运行
```bash
systemctl --user status bobquant-dashboard.service
```

**预期**: `Active: active (running)`

### 3. 检查 Dashboard 是否可访问
```bash
curl http://localhost:8500/api/status
```

**预期**: 返回 JSON 状态信息

### 4. 模拟重启测试
```bash
# 停止所有服务
systemctl --user stop bobquant-dashboard.service bobquant-execution.service

# 启动所有服务
systemctl --user start bobquant-dashboard.service bobquant-execution.service

# 验证
systemctl --user status bobquant-dashboard.service
```

---

## 📝 已完成清理

### Crontab 清理
- ✅ 已删除旧的 `quant_strategies/` 引用
- ✅ 当前 crontab 为空

```bash
$ crontab -l
no crontab for openclaw
```

---

## 🔄 重启后验证

重启电脑后，执行以下命令验证所有服务自动启动：

```bash
# 等待 1 分钟让服务完全启动
sleep 60

# 检查所有服务
systemctl --user status bobquant-dashboard.service bobquant-execution.service openclaw-gateway.service

# 验证 Dashboard
curl http://localhost:8500/api/status

# 验证 WebSocket
curl http://localhost:8500/api/status | python3 -c "import sys,json; d=json.load(sys.stdin); print('WebSocket 客户端:', d['event_bus']['websocket_clients'])"
```

---

## 📊 服务依赖关系

```
openclaw-gateway.service (基础)
    │
    ├── bobquant-dashboard.service
    │   └── 端口：8500
    │
    ├── bobquant-execution.service
    │   └── 模拟交易
    │
    └── bobquant-data-collector.service
        └── 数据采集
```

---

## 🛠️ 故障排查

### Dashboard 无法启动
```bash
# 检查端口占用
lsof -ti:8500

# 查看日志
journalctl --user -u bobquant-dashboard.service -n 50

# 手动测试
cd /home/openclaw/.openclaw/workspace/dashboard && python3 main.py
```

### 服务无法开机自启
```bash
# 重新加载 systemd 配置
systemctl --user daemon-reload

# 重新启用服务
systemctl --user enable bobquant-dashboard.service

# 检查是否启用
systemctl --user list-unit-files --type=service | grep bobquant
```

### 查看服务资源使用
```bash
systemctl --user status bobquant-dashboard.service
# 显示 Memory 和 CPU 使用
```

---

## 📋 配置清单

- [x] Dashboard 服务配置
- [x] Execution Bot 服务配置
- [x] Data Collector 服务配置
- [x] 所有服务启用开机自启
- [x] 旧 crontab 配置清理
- [x] 服务依赖关系配置
- [x] 日志输出配置

---

**配置完成时间**: 2026-04-18 13:27  
**配置者**: BobQuant Team  
**状态**: ✅ 所有服务正常运行
