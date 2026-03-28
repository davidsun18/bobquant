# 🚀 量化模拟盘 - 快速启动指南

**更新时间**: 2026-03-28 17:10  
**状态**: ✅ 已修复，服务正常运行

---

## 🔧 问题原因

重启后没有自动加载，是因为：
1. 原来的 `start_guard.sh` 只启动了 BobQuant 主进程
2. **Web UI 没有配置开机自启动**

---

## ✅ 已修复

### 1. 创建了一键启动脚本
```bash
./start_all.sh
```

**功能**:
- ✅ 自动检查所有进程状态
- ✅ 只启动未运行的服务
- ✅ 记录详细日志
- ✅ 显示访问地址

### 2. 更新开机自启动
```bash
@reboot /home/openclaw/.openclaw/workspace/quant_strategies/start_all.sh
```

**现在重启后会自动启动**:
- ✅ Web UI ( Flask, 5000 端口)
- ✅ BobQuant 主进程 (策略引擎)
- ✅ V2 策略 (如有配置)

---

## 🌐 访问地址

### 当前运行状态
```
✅ Web UI: http://localhost:5000
✅ BobQuant: 运行中 (PID: 602)
✅ 持仓：4 只股票
✅ 现金：约 50 万
```

### 访问方式
1. **本地访问**: http://localhost:5000
2. **局域网访问**: http://192.168.50.55:5000
3. **手机访问**: 同局域网内用手机浏览器打开

---

## 📋 常用命令

### 启动服务
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
./start_all.sh
```

### 停止服务
```bash
./stop_all.sh  # 还没创建，可以手动 kill
```

### 查看状态
```bash
# 查看进程
ps aux | grep -E "web_ui|bobquant" | grep -v grep

# 查看 Web UI 日志
tail -f logs/web_ui.log

# 查看 BobQuant 日志
tail -f logs/bobquant.log

# 查看自动交易日志
tail -f logs/auto_trade.log
```

### 重启服务
```bash
# 方法 1: 全部重启
pkill -f web_ui.py
pkill -f "bobquant/main.py"
./start_all.sh

# 方法 2: 只重启 Web UI
pkill -f web_ui.py
./start_all.sh
```

---

## 🔍 故障排查

### 问题 1: Web UI 打不开
```bash
# 检查进程
ps aux | grep web_ui

# 如果没有运行，启动它
cd /home/openclaw/.openclaw/workspace/quant_strategies
python3 web_ui.py > logs/web_ui.log 2>&1 &

# 检查端口
netstat -tlnp | grep 5000
```

### 问题 2: 数据不更新
```bash
# 查看 BobQuant 进程
ps aux | grep bobquant

# 重启 BobQuant
pkill -f "bobquant/main.py"
cd /home/openclaw/.openclaw/workspace/quant_strategies
python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation &
```

### 问题 3: 自动交易不执行
```bash
# 检查 cron 任务
crontab -l

# 查看自动交易日志
tail -f logs/auto_trade.log

# 手动执行一次
python3 auto_trade_v2.py
```

---

## 📊 当前配置

### 策略配置
- **现有策略**: 网格做 T + 布林带
- **V2 策略**: QuantaAlpha 多因子 (下周一启动)
- **股票池**: 30 只 (银行/白酒/科技/半导体)

### 交易时间
- **自动减仓**: 周一 09:30-10:00
- **V2 建仓**: 周一 10:00-11:00
- **日常检查**: 周一 - 周五 09:00, 14:00

### 风控设置
- **总仓位**: ≤ 80%
- **单只股票**: ≤ 15%
- **现金储备**: ≥ 20%
- **V2 止损**: -10% 硬止损

---

## 📁 重要文件

| 文件 | 说明 | 位置 |
|------|------|------|
| `start_all.sh` | 一键启动脚本 ⭐ | `quant_strategies/` |
| `auto_trade_v2.py` | 自动交易脚本 | `quant_strategies/` |
| `web_ui.py` | Web 界面 | `quant_strategies/` |
| `account_ideal.json` | 账户持仓 | `sim_trading/` |
| `交易记录.json` | 交易历史 | `sim_trading/` |

---

## 🎯 下周一执行计划

### 03-31 (周一) 自动执行
```
09:00 → 自动检查
09:30 → 减仓非划分股票
10:00 → V2 第 1 批建仓
14:00 → V2 第 2 批建仓
15:00 → 收盘检查
```

### 监控方式
```bash
# 实时查看自动交易日志
tail -f logs/auto_trade.log

# 查看持仓变化
watch -n 5 'cat sim_trading/account_ideal.json | jq .positions'
```

---

## 📞 快速帮助

### 服务启动失败？
```bash
./start_all.sh
```

### 想看当前持仓？
```bash
cat sim_trading/account_ideal.json | jq .positions
```

### 想看交易记录？
```bash
tail -20 sim_trading/交易记录.json
```

### 想停止自动交易？
```bash
crontab -e
# 注释掉这两行:
# 0 9 * * 1-5 ...
# 0 14 * * 1-5 ...
```

---

_修复完成：2026-03-28 17:10_  
_服务状态：✅ 正常运行_  
_访问地址：http://localhost:5000_
