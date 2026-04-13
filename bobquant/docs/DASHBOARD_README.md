# BobQuant Dashboard - 交互式可视化

## 📊 功能特性

### 1. K 线蜡烛图（交互式）
- ✅ 标准蜡烛图显示（红涨绿跌）
- ✅ 支持缩放、平移、悬停查看详细信息
- ✅ 实时数据刷新

### 2. 成交量柱状图
- ✅ 与 K 线图同步显示
- ✅ 颜色区分涨跌（红涨绿跌）
- ✅ 悬停显示具体成交量

### 3. 技术指标叠加
- ✅ **MA 均线**: MA5（橙色）、MA10（蓝色）、MA20（紫色）
- ✅ **MACD**: MACD 线、Signal 线、MACD 柱状图
- ✅ **布林带**: 上轨、中轨、下轨 + 布林带宽度%

### 4. 持仓盈亏饼图
- ✅ 环形图设计，显示各股票盈亏占比
- ✅ 颜色区分盈亏（红色盈利、绿色亏损）
- ✅ 悬停显示具体盈亏金额

### 5. 交易记录表格
- ✅ 显示最近 50 条交易记录
- ✅ 包含时间、股票、操作、数量、价格、金额
- ✅ 买入/卖出颜色区分

### 6. 实时刷新
- ✅ 每 3 秒自动刷新所有数据
- ✅ 显示最后更新时间
- ✅ 无需手动刷新页面

## 🚀 启动方式

### 方法 1: 直接启动
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
python3 bobquant/web/dashboard.py
```

### 方法 2: 后台启动
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
nohup python3 bobquant/web/dashboard.py > logs/dashboard.log 2>&1 &
```

### 方法 3: 使用 systemd 服务（推荐生产环境）
```bash
# 创建服务文件
sudo tee /etc/systemd/system/bobquant-dashboard.service > /dev/null <<'EOF'
[Unit]
Description=BobQuant Dashboard
After=network.target

[Service]
Type=simple
User=openclaw
WorkingDirectory=/home/openclaw/.openclaw/workspace/quant_strategies
ExecStart=/usr/bin/python3 bobquant/web/dashboard.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable bobquant-dashboard
sudo systemctl start bobquant-dashboard
```

## 🌐 访问地址

- **本地访问**: http://localhost:8050
- **局域网访问**: http://<本机 IP>:8050
  - 当前 IP: http://192.168.50.55:8050

## 📱 与现有 Web UI 集成

Dashboard 是独立于现有 Flask Web UI 的，两者可以同时运行：

| 服务 | 端口 | 用途 |
|------|------|------|
| Web UI (Flask) | 5000 | 基础持仓、交易记录查看 |
| Dashboard (Dash) | 8050 | 交互式可视化、技术分析 |

### 在 Web UI 中添加 Dashboard 链接

编辑 `templates/index.html`，在导航栏添加：

```html
<a href="http://localhost:8050" class="nav-link" target="_blank">📊 可视化 Dashboard</a>
```

或在 `web_ui.py` 中添加重定向路由：

```python
@app.route('/dashboard')
def dashboard_redirect():
    return redirect('http://localhost:8050')
```

## 🔧 依赖包

```bash
pip3 install plotly dash dash-bootstrap-components
```

或更新依赖：

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
pip3 install -r requirements.txt
```

## 📸 界面预览

### 资产概览
- 总资产、证券市值、可用现金
- 持仓盈亏、当日盈亏（实时计算）

### K 线图区域
- 4 层布局：K 线 + 成交量 + MACD + 布林带
- 支持股票选择器切换不同股票
- 交互式缩放、平移、数据提示

### 持仓盈亏饼图
- 环形图显示各股票盈亏占比
- 直观展示盈利/亏损分布

### 交易记录表格
- 最近 50 条交易记录
- 完整交易信息展示

## ⚙️ 配置说明

### 数据源
- 实时行情：腾讯财经（qt.gtimg.cn）
- 历史 K 线：baostock

### 刷新间隔
- 默认：3 秒
- 修改方法：编辑 `dashboard.py`，找到 `dcc.Interval` 组件，修改 `interval=3*1000`

### 技术指标参数
- MA 周期：5、10、20 日
- MACD：12、26、9
- 布林带：20 日，2 倍标准差

修改方法：编辑 `calculate_indicators()` 函数

## 🐛 常见问题

### Q: Dashboard 无法启动？
A: 检查依赖包是否安装完整：
```bash
pip3 install plotly dash dash-bootstrap-components
```

### Q: 数据不刷新？
A: 检查账户文件路径是否正确：
- 账户文件：`/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/account_ideal.json`
- 交易记录：`/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/交易记录.json`

### Q: K 线图显示"暂无数据"？
A: 检查数据源连接，确保网络正常。历史数据通过 baostock 获取，需要联网。

### Q: 端口被占用？
A: 修改启动端口，编辑 `dashboard.py` 最后一行：
```python
app.run(host='0.0.0.0', port=8051, debug=False)  # 改为其他端口
```

## 📝 更新日志

### v1.0 (2026-04-11)
- ✅ 初始版本发布
- ✅ K 线蜡烛图
- ✅ 成交量柱状图
- ✅ 技术指标（MA/MACD/布林带）
- ✅ 持仓盈亏饼图
- ✅ 交易记录表格
- ✅ 3 秒实时刷新

---

**维护者**: Bob (AI Assistant)  
**最后更新**: 2026-04-11
