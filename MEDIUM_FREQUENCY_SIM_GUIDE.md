# 🧪 中频交易 - 模拟测试指南

**版本**: v1.0  
**创建时间**: 2026-03-29  
**状态**: ✅ 已启动

---

## 🎯 模拟测试目标

| 指标 | 目标值 | 测试周期 |
|------|--------|---------|
| **初始资金** | ¥200,000 | - |
| **预期月收益** | 5-10% | 1 个月 |
| **最大回撤** | <15% | - |
| **胜率** | >55% | - |
| **交易频率** | 3-5 笔/天 | - |

---

## 🚀 快速开始

### 1. 初始化模拟账户

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies

# 创建模拟账户 (初始资金 20 万)
python3 scripts/run_sim_test.py --init --capital 200000
```

### 2. 运行模拟交易

```bash
# 单次检查
python3 scripts/run_sim_test.py --run --once

# 循环监控 (交易时段每 5 分钟检查)
python3 scripts/run_sim_test.py --run
```

### 3. 查看报告

```bash
# 生成交易报告
python3 scripts/run_sim_test.py --report
```

---

## 📊 账户文件

| 文件 | 说明 | 路径 |
|------|------|------|
| `mf_sim_account.json` | 模拟账户数据 | `sim_trading/` |
| `mf_sim_trades.json` | 交易记录 | `sim_trading/` |
| `mf_reports/` | 交易报告 | `sim_trading/` |

---

## ⚙️ 策略参数 (已优化)

### 网格策略
```yaml
grid_size: 0.010           # 网格间距 1.0%
position_per_grid: 0.03    # 每格仓位 3%
max_grids: 10              # 最多 10 格
```

### 波段策略
```yaml
rsi_oversold: 35           # RSI<35 超卖
rsi_overbought: 65         # RSI>65 超买
```

### 动量策略
```yaml
breakout_period: 15        # 突破 15 周期
volume_confirm: 1.3        # 成交量 1.3 倍
```

### 风控配置
```yaml
max_position_per_stock: 0.10   # 单只≤10%
max_total_position: 0.60       # 总仓位≤60%
stop_loss: -0.03               # -3% 止损
take_profit: 0.08              # +8% 止盈
max_consecutive_losses: 3      # 连续亏损 3 笔暂停
```

---

## 📈 股票池 (10 只)

| 代码 | 名称 | 行业 | 权重 |
|------|------|------|------|
| sh.603986 | 兆易创新 | 半导体 | 1.2 |
| sz.002371 | 北方华创 | 半导体 | 1.2 |
| sh.603501 | 韦尔股份 | 半导体 | 1.2 |
| sh.688981 | 中芯国际 | 半导体 | 1.2 |
| sz.002156 | 通富微电 | 半导体 | 1.2 |
| sz.002415 | 海康威视 | 科技 | 1.1 |
| sh.601138 | 工业富联 | 科技 | 1.1 |
| sz.300750 | 宁德时代 | 新能源 | 0.8 |
| sz.002594 | 比亚迪 | 新能源 | 0.8 |
| sh.601012 | 隆基绿能 | 光伏 | 0.8 |

---

## 🔧 定时任务配置

### 方法 1: Cron 定时任务

```bash
# 编辑 crontab
crontab -e

# 添加 (交易时段每 5 分钟检查)
*/5 9-11,13-15 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
```

### 方法 2: Systemd 服务

```bash
# 创建服务文件
sudo vim /etc/systemd/system/mf-sim-trading.service

[Unit]
Description=Medium Frequency Sim Trading
After=network.target

[Service]
Type=simple
User=openclaw
WorkingDirectory=/home/openclaw/.openclaw/workspace/quant_strategies
ExecStart=/usr/bin/python3 scripts/run_sim_test.py --run
Restart=on-failure

[Install]
WantedBy=multi-user.target

# 启动服务
sudo systemctl enable mf-sim-trading
sudo systemctl start mf-sim-trading
```

### 方法 3: 后台运行

```bash
# 使用 nohup
nohup python3 scripts/run_sim_test.py --run > logs/mf_sim.log 2>&1 &

# 查看进程
ps aux | grep run_sim_test

# 停止
pkill -f run_sim_test
```

---

## 📝 监控指标

### 每日检查

```bash
# 查看最新日志
tail -f logs/mf_sim.log

# 查看账户状态
cat sim_trading/mf_sim_account.json | jq .

# 查看今日交易
cat sim_trading/mf_sim_trades.json | jq '.[] | select(.time | contains("2026-03-29"))'
```

### 每周报告

```bash
# 生成周报告
python3 scripts/run_sim_test.py --report

# 查看历史报告
ls -lh sim_trading/mf_reports/
```

### 关键指标

| 指标 | 计算公式 | 健康范围 |
|------|---------|---------|
| **收益率** | (总资产 - 初始)/初始 | 5-10%/月 |
| **胜率** | 盈利交易/总交易 | >55% |
| **盈亏比** | 平均盈利/平均亏损 | >1.5 |
| **最大回撤** | 最大亏损/峰值 | <15% |
| **夏普比率** | 收益/波动 | >1.0 |

---

## ⚠️ 注意事项

### 1. 模拟 vs 实盘

| 项目 | 模拟 | 实盘 |
|------|------|------|
| **成交价格** | 收盘价 | 可能有滑点 |
| **成交概率** | 100% | 可能不成交 |
| **手续费** | 0.03% | 可能更高 |
| **心理因素** | 无 | 贪婪/恐惧 |

### 2. 参数调整

**根据测试结果调整**:

- **胜率低** (<50%): 提高信号阈值
- **交易少** (<3 笔/天): 放宽网格间距
- **回撤大** (>15%): 降低单只仓位
- **盈利少**: 调整止盈比例

### 3. 风险控制

- ❌ 不要频繁修改参数
- ✅ 至少测试 1 周再调整
- ✅ 记录每次参数变更
- ✅ 对比调整前后效果

---

## 📊 示例报告

```
【账户概览】
初始资金：¥200,000.00
当前总资产：¥215,000.00
总盈亏：¥15,000.00 (7.5%)

【交易统计】
总交易次数：45
买入次数：25
卖出次数：20
盈利交易：12 笔，¥18,000
亏损交易：8 笔，¥-5,000
净盈亏：¥13,000
胜率：60%

【策略统计】
grid: 20 笔，¥6,000
swing: 15 笔，¥5,000
momentum: 10 笔，¥2,000

【当前持仓】
sh.603986 兆易创新   1000 股 成本¥95.00 现¥98.00 盈亏¥3,000 (3.16%)
sz.300750 宁德时代    500 股 成本¥180.00 现¥185.00 盈亏¥2,500 (2.78%)
```

---

## 🎯 测试计划

### 第 1 周：观察期
- [ ] 每日检查信号质量
- [ ] 记录交易次数
- [ ] 观察胜率

### 第 2 周：调整期
- [ ] 根据数据调整参数
- [ ] 优化网格间距
- [ ] 调整止损止盈

### 第 3-4 周：稳定期
- [ ] 验证策略稳定性
- [ ] 统计完整月度收益
- [ ] 评估是否转实盘

---

## 📞 常用命令

```bash
# 初始化
python3 scripts/run_sim_test.py --init --capital 200000

# 运行一次
python3 scripts/run_sim_test.py --run --once

# 循环运行
python3 scripts/run_sim_test.py --run

# 生成报告
python3 scripts/run_sim_test.py --report

# 查看日志
tail -f logs/mf_sim.log

# 查看账户
cat sim_trading/mf_sim_account.json | jq .

# 查看交易
cat sim_trading/mf_sim_trades.json | jq '.[] | {time, name, action, price, profit}'
```

---

**模拟测试启动时间**: 2026-03-29  
**预计测试周期**: 2-4 周  
**目标**: 验证策略有效性，为实盘做准备
