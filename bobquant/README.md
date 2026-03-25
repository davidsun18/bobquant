# BobQuant ⚡ — A股量化交易系统

> By David & Bob | v0.1.0 | 2026-03-25

一套面向 A 股市场的模块化量化交易系统，支持模拟盘自动交易，未来可无缝对接实盘券商。

## ✨ 核心特性

### 交易策略
- **MACD 金叉死叉** — 趋势跟踪，支持 RSI 过滤 + 成交量确认
- **布林带突破** — 均值回归，上下轨信号
- **金字塔加仓** — 3% → 5% → 7% 三档递进，跌 3% 触发加仓
- **分批止盈** — 涨 5% 卖 1/3 → 涨 10% 卖 1/2 → 涨 15% 清仓
- **网格做 T** — 日内多档高抛低吸，每涨 1.5% 抛一次，回落 1% 接回
- **跟踪止损** — 盈利 5% 后激活，从最高点回撤 2% 自动卖出

### 信号过滤
- **RSI 过滤** — RSI > 35 不买入（避免追高），RSI > 70 加大减仓力度
- **成交量确认** — 放量金叉标记为强信号，缩量信号过滤掉
- **信号强度分级** — 强信号直接 5% 仓位，普通信号 3% 试探

### 工程架构
- **模块化设计** — 配置/数据/指标/策略/风控/券商/通知 7 层分离
- **可插拔接口** — 数据源、策略、券商都是抽象接口，一键切换
- **零硬编码** — 所有路径自动推导，所有参数 YAML 配置驱动
- **172 个测试** — 单元测试 + 集成测试 + 边界条件 + 压力测试全覆盖
- **进程守护** — 交易时段自动启停，崩溃 30 秒内自动重启
- **开机自启** — crontab @reboot 全自动

## 📁 项目结构

```
bobquant/
├── config/
│   ├── __init__.py          # 配置中心（YAML 驱动，零硬编码）
│   ├── settings.yaml        # 全局配置
│   └── stock_pool.yaml      # 股票池（50只 A 股龙头）
├── indicator/
│   └── technical.py         # MACD / 布林带 / RSI / 量比
├── data/
│   └── provider.py          # 数据源（腾讯财经 + baostock）
├── core/
│   ├── account.py           # 账户 + 持仓 + T+1 管理
│   └── executor.py          # 买入 / 卖出 / 交易记录同步
├── strategy/
│   └── engine.py            # MACD策略 / 布林带策略 / 风控 / 网格做T
├── broker/
│   └── base.py              # 券商抽象（模拟盘 / easytrader 预留）
├── notify/
│   └── feishu.py            # 飞书消息通知
├── tests/
│   ├── test_all.py          # 59 个单元测试
│   └── test_integration.py  # 113 个集成测试
├── main.py                  # 三阶段交易引擎 + 主循环
└── README.md
```

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install pandas requests baostock pyyaml flask
```

### 2. 配置
编辑 `bobquant/config/settings.yaml`，按需修改：
- 初始资金、手续费率
- 策略参数（止损线、止盈档位、做T阈值）
- 数据源选择
- 飞书通知 user_id

### 3. 运行
```bash
python run.py
```

### 4. Web 监控
```bash
python web_ui.py  # 访问 http://localhost:5000
```

## 📊 三阶段交易引擎

每个交易时段，引擎按顺序执行三个阶段：

```
Phase 1: 网格做T
  → 扫描持仓股日内涨幅
  → 触发网格线则高抛，回落则接回

Phase 2: 风控
  → 硬止损（亏 ≥ 8%）
  → 跟踪止损（盈利后从最高点回撤 ≥ 2%）
  → 分批止盈（5% / 10% / 15% 三档）

Phase 3: 策略信号
  → MACD / 布林带信号检测
  → RSI + 成交量双重过滤
  → 新建仓 / 金字塔加仓 / 策略减仓
```

## 🔧 扩展指南

| 要做的事 | 怎么做 |
|----------|--------|
| 加新策略 | 继承 `BaseStrategy`，实现 `check()` 方法 |
| 加新数据源 | 继承 `DataProvider`，实现 `get_quote()` / `get_history()` |
| 加新指标 | 在 `indicator/technical.py` 中添加函数 |
| 对接实盘 | 继承 `BaseBroker`，改 `settings.yaml` 的 `broker.mode` |
| 改交易参数 | 只改 `settings.yaml`，不碰代码 |

## 🧪 测试

```bash
# 单元测试（59个）
python bobquant/tests/test_all.py

# 集成测试（113个，需要网络）
python bobquant/tests/test_integration.py
```

## ⚠️ 免责声明

本系统仅供学习和模拟交易使用。股市有风险，投资需谨慎。作者不对使用本系统产生的任何损失承担责任。

## 📜 License

MIT
