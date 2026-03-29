# 🎊 统一模拟盘系统 - 整合完成

**整合时间**: 2026-03-29 08:45  
**状态**: ✅ 已完成整合

---

## 📊 系统架构

```
统一模拟盘系统
│
├── 日线策略 (主账户)
│   ├── 初始资金：¥1,000,000
│   ├── 当前现金：¥506,841
│   ├── 持仓：19 只股票
│   └── 策略：多因子 + 网格做 T
│
├── 中频交易 (独立账户)
│   ├── 初始资金：¥200,000
│   ├── 当前现金：¥200,000
│   ├── 持仓：0 只 (等待开盘)
│   └── 策略：网格 + 波段 + 动量
│
└── 统一监控
    ├── Web UI: http://localhost:5000
    ├── 合并报告：sim_trading/reports/
    └── 统一日志：logs/sim_trading.log
```

---

## 🚀 启动方法

### 方法 1: 统一启动脚本 (推荐)

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies

# 查看系统状态
python3 scripts/start_sim_trading.py --status

# 启动所有策略
python3 scripts/start_sim_trading.py --all

# 只启动日线策略
python3 scripts/start_sim_trading.py --day

# 只启动中频交易
python3 scripts/start_sim_trading.py --medium

# 生成合并报告
python3 scripts/start_sim_trading.py --report

# 同步账户价格
python3 scripts/start_sim_trading.py --sync
```

### 方法 2: 分别启动

```bash
# 日线策略
python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation

# 中频交易
python3 scripts/run_sim_test.py --run
```

### 方法 3: Web UI 查看

```bash
# 启动 Web UI
python3 web_ui.py

# 访问
http://localhost:5000

# API 端点
/api/account      # 日线账户
/api/mf_account   # 中频账户
/api/combined     # 合并数据
```

---

## 📁 文件结构

```
quant_strategies/
├── scripts/
│   ├── start_sim_trading.py       # ⭐ 统一启动脚本 (新增)
│   ├── run_sim_test.py            # 中频交易模拟
│   └── run_medium_frequency.py    # 中频交易主程序
│
├── sim_trading/
│   ├── account_ideal.json         # 日线账户 (主)
│   ├── 交易记录.json              # 日线交易记录
│   ├── mf_sim_account.json        # 中频账户 (新增)
│   ├── mf_sim_trades.json         # 中频交易记录 (新增)
│   └── reports/                   # 合并报告 (新增)
│
├── medium_frequency/              # 中频交易模块
│   ├── config/mf_config.yaml
│   ├── data_fetcher.py
│   ├── signal_generator.py
│   ├── execution_engine.py
│   └── risk_monitor.py
│
├── bobquant/                      # 日线策略模块
│   ├── main.py
│   ├── strategy/
│   └── config/
│
└── web_ui.py                      # Web 界面 (已更新)
```

---

## 📊 账户管理

### 主账户 (日线策略)

| 项目 | 数值 |
|------|------|
| 初始资金 | ¥1,000,000 |
| 当前现金 | ¥506,841 |
| 持仓数量 | 19 只 |
| 策略类型 | 多因子 + 网格 |

### 中频账户 (中频交易)

| 项目 | 数值 |
|------|------|
| 初始资金 | ¥200,000 |
| 当前现金 | ¥200,000 |
| 持仓数量 | 0 只 |
| 策略类型 | 网格 + 波段 + 动量 |

### 合并统计

| 项目 | 数值 |
|------|------|
| 总初始资金 | ¥1,200,000 |
| 当前总资产 | ¥1,206,841+ |
| 总持仓数量 | 19+ 只 |

---

## ⚙️ 配置说明

### 日线策略配置

```bash
# 配置文件
bobquant/config/sim_config_v2_2.yaml

# 运行命令
python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation
```

### 中频交易配置

```bash
# 配置文件
medium_frequency/config/mf_config.yaml

# 策略参数
grid_size: 0.010          # 网格间距 1%
rsi_oversold: 35          # RSI 超卖
rsi_overbought: 65        # RSI 超买
breakout_period: 15       # 突破周期
```

### 统一监控配置

```bash
# Web UI 端口
5000

# 日志文件
logs/sim_trading.log

# 报告目录
sim_trading/reports/
```

---

## 🔄 数据流

```
┌──────────────────────────────────────┐
│  数据源 (新浪财经/腾讯财经)            │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  统一数据获取层                       │
│  - MinuteDataFetcher (中频)          │
│  - MarketAPI (日线)                  │
└──────────────┬───────────────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
┌─────────────┐ ┌─────────────┐
│ 日线策略    │ │ 中频交易    │
│ 主账户      │ │ 独立账户    │
└──────┬──────┘ └──────┬──────┘
       │               │
       └───────┬───────┘
               │
               ▼
┌──────────────────────────────────────┐
│  统一监控层                           │
│  - Web UI                            │
│  - 合并报告                          │
│  - 统一日志                          │
└──────────────────────────────────────┘
```

---

## 📈 监控指标

### 实时监控

```bash
# 查看系统状态
python3 scripts/start_sim_trading.py --status

# 查看 Web UI
http://localhost:5000

# 查看合并数据
curl http://localhost:5000/api/combined
```

### 日报

```bash
# 生成合并报告
python3 scripts/start_sim_trading.py --report

# 查看报告
ls -lh sim_trading/reports/
cat sim_trading/reports/combined_report_*.md
```

### 周报

```bash
# 每周生成周报
python3 scripts/weekly_summary.py

# 对比两个策略表现
python3 scripts/strategy_comparison.py
```

---

## ⚠️ 注意事项

### 1. 账户独立

- ✅ **主账户**: 日线策略专用，100 万初始资金
- ✅ **中频账户**: 中频交易专用，20 万初始资金
- ✅ **独立风控**: 各自执行止损止盈
- ✅ **合并统计**: Web UI 显示合并数据

### 2. 仓位控制

| 策略 | 单只上限 | 总仓位上限 |
|------|---------|-----------|
| 日线 | 15% | 80% |
| 中频 | 10% | 60% |
| **合并** | **25%** | **140%** |

### 3. 交易时间

| 策略 | 检查频率 | 交易时段 |
|------|---------|---------|
| 日线 | 每日 1 次 | 09:30 |
| 中频 | 每 5 分钟 | 09:30-11:30, 13:00-15:00 |

### 4. 日志管理

```bash
# 日线日志
tail -f logs/bobquant.log

# 中频日志
tail -f logs/mf_sim.log

# 统一日志
tail -f logs/sim_trading.log

# Web UI 日志
tail -f web_ui.log
```

---

## 🎯 运行计划

### 日线策略

```bash
# Cron 配置 (每日 09:30 检查)
0 9 * * 1-5 python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation
```

### 中频交易

```bash
# Cron 配置 (每 5 分钟检查)
*/5 9-11 * * 1-5 python3 scripts/run_sim_test.py --run --once
*/5 12-14 * * 1-5 python3 scripts/run_sim_test.py --run --once
```

### 统一监控

```bash
# 收盘后生成报告 (每日 15:30)
30 15 * * 1-5 python3 scripts/start_sim_trading.py --report
```

---

## 📞 常用命令

```bash
# 查看系统状态
python3 scripts/start_sim_trading.py --status

# 启动所有
python3 scripts/start_sim_trading.py --all

# 生成报告
python3 scripts/start_sim_trading.py --report

# 同步价格
python3 scripts/start_sim_trading.py --sync

# 查看日线账户
cat sim_trading/account_ideal.json | jq .

# 查看中频账户
cat sim_trading/mf_sim_account.json | jq .

# 查看合并数据
curl http://localhost:5000/api/combined | jq .

# 启动 Web UI
python3 web_ui.py
```

---

## 🎊 整合优势

### 1. 独立运行
- ✅ 两个策略互不干扰
- ✅ 各自独立风控
- ✅ 独立账户管理

### 2. 统一监控
- ✅ Web UI 统一展示
- ✅ 合并报告生成
- ✅ 统一日志记录

### 3. 灵活配置
- ✅ 可单独启动
- ✅ 可同时运行
- ✅ 可调整资金分配

### 4. 易于扩展
- ✅ 可添加新策略
- ✅ 可调整参数
- ✅ 可对比策略表现

---

## 📝 下一步

### 第 1 周：观察期
- [ ] 监控中频交易信号
- [ ] 对比两个策略表现
- [ ] 调整参数优化

### 第 2 周：优化期
- [ ] 根据数据调整参数
- [ ] 优化资金分配
- [ ] 完善监控报告

### 第 3-4 周：稳定期
- [ ] 验证策略稳定性
- [ ] 统计月度收益
- [ ] 评估实盘可行性

---

**整合完成时间**: 2026-03-29 08:45  
**系统状态**: ✅ 已就绪  
**等待开盘**: 2026-03-31 09:30
