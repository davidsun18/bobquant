# BobQuant Web 模块

Streamlit 看板、Plotly Dash、统一导航页。

---

## 📁 模块结构

```
web/
├── __init__.py              # 模块导出
├── streamlit_app.py         # Streamlit 应用
├── dashboard.py             # Dash 看板
├── index.html               # 统一导航页
└── DEPLOYMENT_SUMMARY.md    # 部署说明
```

---

## 🚀 快速开始

### 1. 启动 Streamlit

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
./start_streamlit.sh
```

访问：http://localhost:8501

### 2. 启动 Dash

```bash
python3 web/dashboard.py
```

访问：http://localhost:8050

### 3. 启动导航页

```bash
./start_nav_page.sh
```

访问：http://localhost:8502

---

## 📊 Streamlit 看板

### 页面结构

```
🚀 BobQuant Streamlit
│
├── 📊 账户概览
│   ├── 关键指标卡片
│   ├── 资金曲线图
│   └── 持仓明细表格
│
├── 📈 持仓分析
│   ├── 持仓占比饼图
│   ├── 盈亏分布柱状图
│   └── K 线图
│
├── 📝 交易记录
│   ├── 交易历史表格
│   └── 交易统计
│
├── 📈 绩效分析
│   ├── 关键绩效指标
│   ├── 资金曲线
│   └── 月度收益分布
│
└── ⚙️ 设置
    ├── 数据源配置
    └── 缓存管理
```

### 功能特点

- ✅ 多页面导航
- ✅ 实时数据刷新 (30 秒)
- ✅ 交互式图表 (Plotly)
- ✅ 数据筛选
- ✅ 响应式设计

---

## 📈 Plotly Dash 看板

### 功能特点

- ✅ 实时监控 (3 秒刷新)
- ✅ 单页面展示
- ✅ 自动更新
- ✅ 轻量级

---

## 🔧 配置说明

### Streamlit 配置

```bash
# 启动命令
streamlit run web/streamlit_app.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --server.headless true
```

### Dash 配置

```python
app = dash.Dash(__name__)
app.run_server(
    host='0.0.0.0',
    port=8050,
    debug=False
)
```

---

## 📚 相关文档

- [Streamlit 详细文档](./STREAMLIT_README.md)
- [部署说明](./DEPLOYMENT_SUMMARY.md)

---

**最后更新**: 2026-04-11  
**维护者**: BobQuant Team
