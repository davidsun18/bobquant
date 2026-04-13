# BobQuant Streamlit 可视化看板

## 📊 概述

BobQuant Streamlit 可视化看板是一个基于 Streamlit 构建的多页面交互式 Web 界面，用于实时监控和分析量化交易账户状态。

## ✨ 功能特性

### 1. 账户概览 (Overview)
- 💰 总资产实时展示
- 📈 证券市值与可用现金
- 📊 持仓盈亏统计
- 💹 资金曲线图
- 📋 持仓明细表格

### 2. 持仓分析 (Positions)
- 🥧 持仓占比饼图
- 📊 个股盈亏分布柱状图
- 📋 详细持仓信息表
- 📈 K 线蜡烛图（支持技术指标）
  - MA5/MA10/MA20 均线
  - MACD 指标
  - 布林带

### 3. 交易记录 (Trades)
- 📝 完整交易历史
- 🔍 多维度筛选（股票、操作类型）
- 📊 交易统计（买入/卖出次数）

### 4. 绩效分析 (Performance)
- 📊 关键绩效指标
  - 初始资金
  - 当前资产
  - 绝对收益
  - 估算年化收益
- 💹 资金曲线
- 📅 月度收益分布

### 5. 设置 (Settings)
- ⚙️ 数据源配置信息
- 🗑️ 缓存管理
- 📖 功能对比说明

## 🚀 快速启动

### 方法一：使用启动脚本
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
./start_streamlit.sh
```

### 方法二：直接启动
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
streamlit run web/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

### 方法三：后台运行
```bash
nohup streamlit run web/streamlit_app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true > /tmp/streamlit.log 2>&1 &
```

## 🌐 访问地址

- **本地访问**: http://localhost:8501
- **局域网访问**: http://<本机 IP>:8501
- **外部访问**: http://112.9.38.62:8501 (需确保防火墙允许)

## 📁 文件结构

```
bobquant/
├── web/
│   ├── __init__.py
│   ├── dashboard.py          # 原有的 Plotly Dash 看板
│   └── streamlit_app.py      # 新增的 Streamlit 看板 ⭐
├── start_streamlit.sh        # 启动脚本 ⭐
└── STREAMLIT_README.md       # 本文档 ⭐
```

## 🔄 与现有 WEB UI 集成

### 1. 并行运行
Streamlit 看板与现有的 Plotly Dash 看板可以并行运行：

| 看板 | 端口 | 特点 |
|------|------|------|
| Plotly Dash | 8050 | 单页面、实时刷新（3 秒） |
| Streamlit | 8501 | 多页面、功能丰富 |

### 2. 统一入口（可选）
创建一个简单的 HTML 导航页：

```html
<!DOCTYPE html>
<html>
<head>
    <title>BobQuant 可视化看板</title>
    <style>
        body { font-family: Arial; text-align: center; padding: 50px; }
        .card { display: inline-block; margin: 20px; padding: 30px; border: 1px solid #ddd; border-radius: 10px; }
        a { text-decoration: none; color: #667eea; font-size: 20px; }
    </style>
</head>
<body>
    <h1>🚀 BobQuant 可视化看板</h1>
    <div class="card">
        <a href="http://localhost:8050" target="_blank">📊 Plotly Dash 看板</a>
        <p>单页面、实时刷新（3 秒）</p>
    </div>
    <div class="card">
        <a href="http://localhost:8501" target="_blank">📈 Streamlit 看板</a>
        <p>多页面、功能丰富</p>
    </div>
</body>
</html>
```

保存为 `web/index.html`，访问 `http://localhost:8502`（需要简单的 HTTP 服务器）。

### 3. Nginx 反向代理（生产环境推荐）
```nginx
server {
    listen 80;
    server_name bobquant.local;

    location /dash/ {
        proxy_pass http://localhost:8050/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /streamlit/ {
        proxy_pass http://localhost:8501/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📊 页面结构

```
Streamlit 应用
├── 📊 账户概览 (page_overview)
│   ├── 关键指标卡片（4 个）
│   ├── 资金曲线图
│   └── 持仓明细表格
│
├── 📈 持仓分析 (page_positions)
│   ├── 持仓占比饼图
│   ├── 盈亏分布柱状图
│   ├── 持仓详情表格
│   └── K 线图（可选股票）
│
├── 📝 交易记录 (page_trades)
│   ├── 筛选器（股票、操作类型）
│   ├── 交易记录表格
│   └── 交易统计
│
├── 📈 绩效分析 (page_performance)
│   ├── 关键绩效指标（4 个）
│   ├── 资金曲线
│   └── 月度收益分布
│
└── ⚙️ 设置 (page_settings)
    ├── 数据源配置
    ├── 刷新频率说明
    ├── 访问地址
    └── 功能对比表
```

## 🔧 配置说明

### 数据文件路径
- **账户文件**: `/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/account_ideal.json`
- **交易记录**: `/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/交易记录.json`

### 缓存策略
- 使用 `@st.cache_data(ttl=30)` 实现 30 秒自动缓存更新
- 手动刷新按钮可立即清除缓存并重载数据

### 数据源
- 使用腾讯财经 API 获取实时行情
- 历史 K 线数据支持 60 天

## 🎨 技术栈

- **前端框架**: Streamlit 1.x
- **图表库**: Plotly
- **数据处理**: Pandas, NumPy
- **数据源**: BobQuant 内部模块

## 📝 使用技巧

### 1. 实时刷新
- 页面数据每 30 秒自动更新
- 点击侧边栏或页面中的"刷新数据"按钮可手动刷新

### 2. 图表交互
- 所有 Plotly 图表支持缩放、平移、悬停查看详细信息
- K 线图支持选择不同股票查看

### 3. 数据筛选
- 交易记录页面支持按股票和操作类型筛选
- 持仓分析页面可选择特定股票查看 K 线

### 4. 性能优化
- 使用缓存减少 API 调用
- 大数据量表格使用 Streamlit 的分页显示

## 🆚 与 Plotly Dash 看板对比

| 功能 | Streamlit | Plotly Dash |
|------|-----------|-------------|
| 账户概览 | ✅ | ✅ |
| 持仓分析 | ✅ | ✅ |
| 交易记录 | ✅ | ✅ |
| 绩效图表 | ✅ | ❌ |
| 多页面导航 | ✅ | ❌ |
| K 线图表 | ✅ | ✅ |
| 实时刷新 | ✅ (30 秒) | ✅ (3 秒) |
| 代码复杂度 | 低 | 中 |
| 扩展性 | 高 | 中 |
| 部署难度 | 低 | 中 |

## 🐛 故障排查

### 1. 无法访问
```bash
# 检查进程
ps aux | grep streamlit

# 检查端口
netstat -tlnp | grep 8501

# 查看日志
tail -f /tmp/streamlit.log
```

### 2. 数据不更新
```bash
# 清除缓存
# 在设置页面点击"清除缓存"按钮

# 重启服务
pkill -f "streamlit run"
./start_streamlit.sh
```

### 3. 图表不显示
- 检查是否安装 plotly: `pip3 list | grep plotly`
- 检查数据文件是否存在
- 查看浏览器控制台错误信息

## 📈 未来改进

- [ ] 添加更多技术指标
- [ ] 支持自定义时间范围
- [ ] 添加预警功能
- [ ] 支持导出报表
- [ ] 移动端适配
- [ ] 添加用户认证

## 📄 许可证

与 BobQuant 主项目保持一致。

---

**创建时间**: 2026-04-11  
**版本**: v1.0  
**作者**: BobQuant Team
