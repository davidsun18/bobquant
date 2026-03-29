# ✅ Web UI 已启动并运行！

**状态**: ✅ 正常运行  
**时间**: 2026-03-29 09:05

---

## 🌐 访问地址

### 1. 中频交易监控页面 ⭐
```
http://localhost:5000/mf
```

### 2. 主页 (合并展示)
```
http://localhost:5000
```

### 3. API 接口
```
http://localhost:5000/api/mf_account    # 中频账户数据
http://localhost:5000/api/combined      # 合并数据
http://localhost:5000/api/account       # 日线账户
http://localhost:5000/api/trades        # 交易记录
```

---

## 📊 测试结果

### ✅ API 测试
```bash
curl http://localhost:5000/api/mf_account
```

**返回**:
```json
{
  "cash": 200000.0,
  "initial_capital": 200000.0,
  "total_value": 200000.0,
  "total_pnl": 0.0,
  "positions": {},
  ...
}
```

### ✅ 页面测试
```bash
curl http://localhost:5000/mf
```

**返回**: HTML 页面正常加载

---

## 🚀 立即访问

### 方法 1: 本地浏览器
打开浏览器，访问：
```
http://localhost:5000/mf
```

### 方法 2: 手机访问 (局域网)
1. 查看本机 IP:
   ```bash
   hostname -I
   ```

2. 手机浏览器访问:
   ```
   http://[本机 IP]:5000/mf
   例如：http://192.168.1.100:5000/mf
   ```

---

## 📊 页面展示

### 中频监控页面 (http://localhost:5000/mf)

**顶部统计**:
- 💰 初始资金：¥200,000
- 📈 总资产：¥200,000
- 📊 总盈亏：¥0 (0.00%)
- 💵 可用现金：¥200,000
- 📦 持仓数量：0 只

**策略配置**:
- 📐 网格策略：1.0% 间距，3% 每格，10 格
- 🌊 波段策略：RSI 35/65, MACD 12,26,9
- 🚀 动量策略：突破 15 周期，成交量 1.3x

**持仓表格**: (等待开盘后有持仓)
- 代码、名称、股数、成本价、现价、市值、盈亏、盈亏率

**交易记录**: (等待交易后显示)
- 时间、股票、买卖方向、股数、价格、盈亏

---

## 🔧 管理命令

### 查看进程
```bash
ps aux | grep web_ui
```

### 重启 Web UI
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
pkill -f web_ui.py
python3 web_ui.py &
```

### 查看日志
```bash
tail -f logs/web_ui.log
```

### 停止 Web UI
```bash
pkill -f web_ui.py
```

---

## ⚠️ 故障排查

### 问题 1: 页面打不开

**检查进程**:
```bash
ps aux | grep web_ui
```

**如果没有运行**:
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
python3 web_ui.py &
```

**查看错误**:
```bash
tail -30 logs/web_ui.log
```

### 问题 2: 端口被占用

**查看占用**:
```bash
netstat -tlnp | grep 5000
```

**杀死进程**:
```bash
pkill -9 -f web_ui.py
```

**重启**:
```bash
python3 web_ui.py &
```

### 问题 3: API 返回 404

**检查路由**:
```bash
curl http://localhost:5000/api/mf_account
```

**如果还是 404，重启 Web UI**:
```bash
pkill -f web_ui.py
python3 web_ui.py &
```

---

## 📝 后台运行 (推荐)

```bash
# 使用 nohup 后台运行
cd /home/openclaw/.openclaw/workspace/quant_strategies
nohup python3 web_ui.py > logs/web_ui.log 2>&1 &

# 查看进程
ps aux | grep web_ui

# 查看日志
tail -f logs/web_ui.log
```

---

## 🎯 下一步

### 1. 现在就可以访问
```
http://localhost:5000/mf
```

### 2. 配置自动启动
已配置在 Cron 中：
```bash
@reboot /home/openclaw/.openclaw/workspace/quant_strategies/start_all.sh
```

### 3. 等待周一开盘
- 周一 09:30 后会有实时数据
- 每 5 秒自动刷新
- 自动生成交易记录

---

## 🎊 完成！

**Web UI 已正常启动！**

现在可以打开浏览器访问：
```
http://localhost:5000/mf
```

看到中频交易监控页面了！🎉

---

**启动时间**: 2026-03-29 09:05  
**状态**: ✅ 正常运行  
**进程 PID**: 54231
