# 🚀 BobQuant Streamlit - 快速开始指南

## ⚡ 30 秒快速启动

### 方式一：启动 Streamlit 看板
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
./start_streamlit.sh
```
**访问**: http://localhost:8501

### 方式二：启动统一导航页
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
./start_nav_page.sh
```
**访问**: http://localhost:8502

---

## 📊 访问地址速查

| 看板 | 地址 | 特点 |
|------|------|------|
| Streamlit | http://localhost:8501 | 多页面、功能丰富 |
| Plotly Dash | http://localhost:8050 | 单页面、实时刷新 |
| 统一导航 | http://localhost:8502 | 统一入口 |

---

## 🎯 5 个页面功能

1. **📊 账户概览**: 总资产、资金曲线、持仓明细
2. **📈 持仓分析**: 持仓占比、盈亏分布、K 线图
3. **📝 交易记录**: 历史交易、筛选统计
4. **📈 绩效分析**: 关键指标、月度收益
5. **⚙️ 设置**: 配置信息、缓存管理

---

## 🔧 常用命令

```bash
# 查看运行状态
ps aux | grep streamlit

# 查看日志
tail -f /tmp/streamlit.log

# 停止服务
pkill -f "streamlit run"

# 重启服务
pkill -f "streamlit run"
./start_streamlit.sh
```

---

## 📖 详细文档

- **STREAMLIT_README.md** - 完整使用文档
- **集成完成报告.md** - 项目总结报告
- **web/DEPLOYMENT_SUMMARY.md** - 部署详情

---

## ✅ 当前状态

- Streamlit 服务：✅ 运行中 (PID: 431743)
- 端口监听：✅ 8501
- 健康检查：✅ 通过
- 数据文件：✅ 已加载

---

**提示**: 首次访问可能需要 5-10 秒加载时间，请耐心等待。
