# 🌐 Web UI 访问指南

**更新时间**: 2026-03-29 08:52  
**状态**: ✅ 已就绪

---

## 📊 访问地址

### 主页面

| 页面 | URL | 说明 |
|------|-----|------|
| **主页** | http://localhost:5000 | 日线策略 + 中频交易合并展示 |
| **中频监控** | http://localhost:5000/mf | 中频交易专用监控页面 ⭐ |
| **合并 API** | http://localhost:5000/api/combined | 合并数据 JSON |
| **中频 API** | http://localhost:5000/api/mf_account | 中频账户 JSON |

---

## 🎨 页面展示

### 1. 主页 (http://localhost:5000)

**展示内容**:
- ✅ 总资产概览
- ✅ 日线策略持仓
- ✅ 中频交易持仓
- ✅ 合并盈亏统计
- ✅ 交易记录

**刷新频率**: 5 秒自动刷新

---

### 2. 中频交易专用监控 (http://localhost:5000/mf) ⭐

**展示内容**:

#### 📊 账户统计
- 初始资金 (¥200,000)
- 总资产
- 总盈亏
- 可用现金
- 持仓数量

#### 🎯 策略配置
- **网格策略**: 网格间距 1.0%, 每格 3%, 最大 10 格
- **波段策略**: RSI 超卖 35/超买 65, MACD 12,26,9
- **动量策略**: 突破 15 周期，成交量 1.3x 确认

#### 📦 当前持仓
| 列名 | 说明 |
|------|------|
| 代码 | 股票代码 |
| 名称 | 股票名称 |
| 股数 | 持仓数量 |
| 成本价 | 平均成本 |
| 现价 | 实时价格 |
| 市值 | 持仓市值 |
| 盈亏 | 浮动盈亏 |
| 盈亏率 | 盈亏百分比 |

#### 📝 最近交易
- 交易时间
- 股票名称
- 买卖方向
- 交易股数
- 成交价格
- 盈亏金额

**刷新频率**: 5 秒自动刷新

---

## 🚀 启动 Web UI

### 方法 1: 手动启动

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
python3 web_ui.py
```

### 方法 2: 后台运行

```bash
nohup python3 web_ui.py > web_ui.log 2>&1 &

# 查看进程
ps aux | grep web_ui

# 停止
pkill -f web_ui.py
```

### 方法 3: 开机自启动

已配置在 Cron 中：
```bash
@reboot /home/openclaw/.openclaw/workspace/quant_strategies/start_all.sh
```

---

## 📱 访问方式

### 本地访问
```
http://localhost:5000
http://127.0.0.1:5000
```

### 局域网访问
```
http://[本机 IP]:5000
例如：http://192.168.1.100:5000
```

### 手机访问
在同一个局域网内，用手机浏览器访问：
```
http://[本机 IP]:5000/mf
```

---

## 🔧 配置说明

### 端口配置

Web UI 默认使用 **5000 端口**

如需修改，编辑 `web_ui.py`:
```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```

### 刷新频率

默认 **5 秒** 自动刷新

修改 `templates/mf_monitor.html`:
```javascript
// 每 5 秒刷新一次
setInterval(loadData, 5000);
```

---

## 📊 API 接口

### 1. 合并账户数据

**URL**: `GET /api/combined`

**返回**:
```json
{
  "day_trading": {
    "initial": 1000000,
    "total": 1008144,
    "pnl": 8144,
    "pnl_pct": 0.81,
    "positions": 19
  },
  "medium_frequency": {
    "initial": 200000,
    "total": 200000,
    "pnl": 0,
    "pnl_pct": 0,
    "positions": 0
  },
  "combined": {
    "initial": 1200000,
    "total": 1208144,
    "pnl": 8144,
    "pnl_pct": 0.68
  }
}
```

### 2. 中频账户数据

**URL**: `GET /api/mf_account`

**返回**:
```json
{
  "type": "medium_frequency_sim",
  "created_at": "2026-03-29 08:37:17",
  "initial_capital": 200000,
  "cash": 200000,
  "positions": {},
  "total_value": 200000,
  "daily_pnl": 0,
  "total_pnl": 0
}
```

### 3. 日线账户数据

**URL**: `GET /api/account`

**返回**:
```json
{
  "timestamp": "2026-03-29 08:52:00",
  "initial_capital": 1000000,
  "cash": 506841,
  "market_value": 501303,
  "total_assets": 1008144,
  "total_profit": 8144,
  "positions": [...]
}
```

### 4. 交易记录

**URL**: `GET /api/trades`

**返回**:
```json
{
  "trades": [
    {
      "time": "2026-03-24 09:30:00",
      "code": "sh.600887",
      "name": "伊利股份",
      "action": "买入",
      "shares": 1300,
      "price": 25.61,
      "amount": 33293
    }
  ]
}
```

---

## 🎨 页面截图说明

### 中频监控页面特色

1. **渐变背景** - 紫色渐变主题
2. **卡片式布局** - 数据统计卡片
3. **实时刷新** - 5 秒自动更新
4. **响应式设计** - 支持手机/平板
5. **盈亏颜色** - 盈利绿色，亏损红色

---

## ⚠️ 注意事项

### 1. Web UI 未运行

```bash
# 检查进程
ps aux | grep web_ui

# 启动
python3 web_ui.py

# 查看端口
netstat -tlnp | grep 5000
```

### 2. 页面空白

- 检查浏览器控制台是否有错误
- 确认 Web UI 已启动
- 清除浏览器缓存

### 3. 数据不更新

- 检查账户文件是否存在
- 查看 Web UI 日志：`tail -f web_ui.log`
- 重启 Web UI: `pkill -f web_ui && python3 web_ui.py &`

### 4. 端口被占用

```bash
# 查看占用端口的进程
lsof -i :5000

# 杀死进程
kill -9 [PID]

# 或者修改 web_ui.py 使用其他端口
```

---

## 📞 常用命令

```bash
# 启动 Web UI
python3 web_ui.py

# 后台启动
nohup python3 web_ui.py > web_ui.log 2>&1 &

# 查看进程
ps aux | grep web_ui

# 停止 Web UI
pkill -f web_ui.py

# 查看日志
tail -f web_ui.log

# 测试 API
curl http://localhost:5000/api/combined
curl http://localhost:5000/api/mf_account

# 查看端口
netstat -tlnp | grep 5000
```

---

## 🎯 推荐访问流程

### 第 1 步：启动 Web UI

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
python3 web_ui.py
```

### 第 2 步：访问主页

浏览器打开：http://localhost:5000

查看：
- 总资产
- 日线策略表现
- 中频交易表现
- 合并统计

### 第 3 步：访问中频监控

浏览器打开：http://localhost:5000/mf

查看：
- 中频账户详情
- 策略配置
- 持仓明细
- 交易记录

### 第 4 步：手机监控

在手机浏览器访问：
```
http://[本机 IP]:5000/mf
```

---

## 🎊 页面特色

### 1. 实时数据
- ✅ 5 秒自动刷新
- ✅ 实时价格更新
- ✅ 盈亏实时计算

### 2. 美观界面
- ✅ 渐变背景
- ✅ 卡片布局
- ✅ 响应式设计

### 3. 数据完整
- ✅ 账户统计
- ✅ 策略配置
- ✅ 持仓明细
- ✅ 交易记录

### 4. 多端支持
- ✅ 电脑浏览器
- ✅ 手机浏览器
- ✅ 平板浏览器

---

**创建时间**: 2026-03-29  
**状态**: ✅ 已就绪  
**访问**: http://localhost:5000/mf
