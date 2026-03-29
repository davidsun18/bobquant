# 🎊 中频交易模拟测试 - 启动完成

**启动时间**: 2026-03-29 08:38  
**状态**: ✅ 已就绪，等待开盘

---

## 📊 系统状态

| 组件 | 状态 | 说明 |
|------|------|------|
| **模拟账户** | ✅ 已创建 | 初始资金 ¥200,000 |
| **数据接口** | ✅ 新浪财经 | 5 分钟 K 线 |
| **策略引擎** | ✅ 已加载 | 网格 + 波段 + 动量 |
| **风控系统** | ✅ 已配置 | 仓位/止损/连续亏损 |
| **执行引擎** | ✅ 就绪 | 模拟模式 |
| **日志系统** | ✅ 已配置 | 自动记录 |

---

## 🎯 配置参数

### 账户配置
```
初始资金：¥200,000
股票池：10 只 (半导体/科技/新能源)
交易模式：模拟 (dry_run=False)
```

### 策略参数 (已优化)
```
网格间距：1.0%    (原 1.5%)
RSI 超卖：35      (原 30)
RSI 超买：65      (原 70)
突破周期：15      (原 20)
成交量确认：1.3x  (原 1.5x)
```

### 风控配置
```
单只仓位：≤10%
总仓位：≤60%
止损：-3%
止盈：+8%
连续亏损：3 笔暂停
```

---

## 🚀 启动命令

### 手动运行
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies

# 单次检查
python3 scripts/run_sim_test.py --run --once

# 循环监控
python3 scripts/run_sim_test.py --run
```

### 自动运行 (Cron)
```bash
# 编辑 crontab
crontab -e

# 添加 (交易时段每 5 分钟检查)
*/5 9-11 * * 1-5 python3 scripts/run_sim_test.py --run --once
*/5 12-14 * * 1-5 python3 scripts/run_sim_test.py --run --once
```

### 查看报告
```bash
# 生成报告
python3 scripts/run_sim_test.py --report

# 查看日志
tail -f logs/mf_sim.log
```

---

## 📈 监控指标

### 每日检查清单
- [ ] 查看日志：`tail -f logs/mf_sim.log`
- [ ] 检查信号：生成信号数量
- [ ] 检查交易：执行交易数量
- [ ] 检查盈亏：当日盈亏
- [ ] 检查风控：有无触发暂停

### 每周检查清单
- [ ] 生成周报告
- [ ] 统计胜率
- [ ] 统计盈亏比
- [ ] 检查最大回撤
- [ ] 评估参数有效性

### 月度检查清单
- [ ] 月度收益率
- [ ] 夏普比率
- [ ] 最大回撤
- [ ] 策略对比
- [ ] 决定是否转实盘

---

## 📝 文件结构

```
quant_strategies/
├── scripts/
│   ├── run_sim_test.py          # 模拟测试主程序 ⭐
│   ├── run_medium_frequency.py  # 中频交易主程序
│   └── test_medium_frequency.py # 完整测试脚本
│
├── medium_frequency/
│   ├── config/
│   │   └── mf_config.yaml       # 策略配置 ⭐
│   ├── data_fetcher.py
│   ├── signal_generator.py
│   ├── execution_engine.py
│   └── risk_monitor.py
│
├── sim_trading/
│   ├── mf_sim_account.json      # 模拟账户 ⭐
│   ├── mf_sim_trades.json       # 交易记录 ⭐
│   └── mf_reports/              # 交易报告
│
└── logs/
    └── mf_sim.log               # 运行日志 ⭐
```

---

## ⏰ 交易时间

| 时段 | 时间 | 状态 |
|------|------|------|
| **早盘** | 09:30-11:30 | ✅ 监控中 |
| **午休** | 11:30-13:00 | ⏸️ 暂停 |
| **午盘** | 13:00-15:00 | ✅ 监控中 |
| **收盘** | 15:00 后 | ⏹️ 停止 |
| **周末** | 周六日 | ⏹️ 休市 |

---

## 🎯 测试目标

| 指标 | 目标值 | 周期 |
|------|--------|------|
| **月收益率** | 5-10% | 1 个月 |
| **胜率** | >55% | - |
| **盈亏比** | >1.5 | - |
| **最大回撤** | <15% | - |
| **夏普比率** | >1.0 | - |
| **交易频率** | 3-5 笔/天 | - |

---

## ⚠️ 注意事项

### 1. 周末休市
- 当前是周末 (2026-03-29 周日)
- 周一 (03-31) 开盘后才有信号
- Cron 任务已配置为周一 - 周五运行

### 2. 参数调整
- 至少观察 1 周再调整
- 记录每次参数变更
- 对比调整前后效果

### 3. 风险控制
- 严格执行止损止盈
- 连续亏损 3 笔自动暂停
- 单只股票不超过 10%

---

## 📞 快速命令

```bash
# 初始化账户
python3 scripts/run_sim_test.py --init --capital 200000

# 运行一次
python3 scripts/run_sim_test.py --run --once

# 循环运行
python3 scripts/run_sim_test.py --run

# 生成报告
python3 scripts/run_sim_test.py --report

# 查看账户
cat sim_trading/mf_sim_account.json | jq .

# 查看交易
cat sim_trading/mf_sim_trades.json | jq '.[] | {time, name, action, profit}'

# 查看日志
tail -f logs/mf_sim.log

# 配置 Cron
crontab -e
```

---

## 📊 下次检查时间

**周一开盘**: 2026-03-31 09:30

届时系统将自动：
1. ✅ 获取 10 只股票的 5 分钟 K 线
2. ✅ 计算技术指标 (MACD/RSI/布林带)
3. ✅ 生成交易信号 (网格/波段/动量)
4. ✅ 执行风控检查
5. ✅ 执行交易 (模拟)
6. ✅ 记录日志

---

## 🎉 准备就绪！

**模拟测试系统已启动**  
**等待周一开盘运行**

有任何问题随时查看日志或生成报告！📈

---

_创建时间：2026-03-29 08:38_  
_状态：✅ 已就绪_
