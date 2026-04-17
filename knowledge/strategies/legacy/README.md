# BobQuant 量化交易系统

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-3.0-green.svg)](https://github.com/davidsun18/bobquant)

**BobQuant** 是一个功能完整的量化交易系统，支持 A 股、加密货币等多市场交易。系统采用模块化设计，提供策略开发、回测、实盘交易、风险控制、数据分析和可视化等全流程支持。

---

## 📖 文档导航

### 🚀 快速开始
- [快速开始指南](./QUICKSTART.md) - 5 分钟上手 BobQuant
- [安装部署](./docs/INSTALLATION.md) - 详细安装步骤
- [配置说明](./config/README.md) - 配置系统使用指南

### 📚 核心文档
- [系统架构](./docs/ARCHITECTURE.md) - 整体架构设计
- [API 参考](./docs/API_REFERENCE.md) - 完整 API 文档
- [最佳实践](./docs/BEST_PRACTICES.md) - 开发和使用建议
- [故障排查](./docs/TROUBLESHOOTING.md) - 常见问题解决

### 💻 代码示例
- [示例集合](./docs/EXAMPLES.md) - 常用代码示例
- [策略示例](./strategy/EXAMPLES.md) - 策略开发示例
- [工具示例](./tools/EXAMPLES.md) - 工具使用示例

### 📊 模块文档
| 模块 | 文档 | 说明 |
|------|------|------|
| **核心** | [core/README.md](./core/README.md) | 账户、执行器、风控 |
| **策略** | [strategy/README.md](./strategy/README.md) | 策略引擎、多因子、网格 T |
| **数据** | [data/README.md](./data/README.md) | 数据源、行情接口 |
| **指标** | [indicator/README.md](./indicator/README.md) | 技术指标、TA-Lib |
| **工具** | [tools/README.md](./tools/README.md) | 工具系统、交易工具 |
| **配置** | [config/README.md](./config/README.md) | 配置管理、SecretRef |
| **Web** | [web/README.md](./web/README.md) | Streamlit、Dash 看板 |
| **回测** | [backtest/README.md](./backtest/README.md) | 回测引擎、VectorBT |
| **风控** | [risk_management/README.md](./risk_management/README.md) | 风险管理模块 |
| **事件** | [event/README.md](./event/README.md) | 事件驱动系统 |
| **机器学习** | [ml/README.md](./ml/README.md) | ML 策略、特征工程 |
| **强化学习** | [rl/README.md](./rl/README.md) | RL 策略集成 |
| **优化** | [optimize/README.md](./optimize/README.md) | Optuna 参数优化 |
| **通知** | [notify/README.md](./notify/README.md) | 飞书、微信通知 |
| **权限** | [permissions/README.md](./permissions/README.md) | 权限管理系统 |
| **遥测** | [telemetry/README.md](./telemetry/README.md) | 监控和日志 |

### 📈 专题文档
- [多因子策略](./backtest/MULTIFRAME_GUIDE.md) - 多因子策略指南
- [VectorBT 回测](./backtest/VECTORBT_INTEGRATION.md) - 高性能回测
- [TA-Lib 使用](./indicator/TALIB_ADVANCED_USAGE.md) - 技术指标库
- [Optuna 优化](./optimize/OPTUNA_INTEGRATION_SUMMARY.md) - 参数优化
- [Streamlit 看板](./STREAMLIT_README.md) - 可视化看板
- [TWAP 执行](./TWAP_USAGE.md) - 算法交易执行

---

## ⚡ 快速开始

### 1. 克隆仓库
```bash
git clone https://github.com/davidsun18/bobquant.git
cd bobquant
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置系统
```bash
# 复制配置示例
cp config/config_example.json5 config/settings.json5

# 编辑配置（设置 API 密钥等）
vim config/settings.json5
```

### 4. 启动系统
```bash
# 启动主程序
python3 main.py

# 或启动模拟盘
./start_sim_v2_2.sh

# 启动 Web 看板
./start_streamlit.sh
```

### 5. 访问看板
- **Streamlit**: http://localhost:8501
- **统一导航**: http://localhost:8502

---

## 🎯 核心特性

### 📊 多市场支持
- ✅ **A 股**: 沪深股市、ETF、可转债
- ✅ **加密货币**: 比特币、以太坊等主流币种
- ✅ **美股**: 支持通过 yfinance 获取数据

### 🧠 策略系统
- **多因子策略**: 基于基本面、技术面、情绪面的多因子选股
- **网格 T+0**: 日内回转交易策略
- **高频策略**: 毫秒级高频交易
- **机器学习**: ML 预测模型集成
- **强化学习**: RL 策略优化
- **再平衡策略**: 定期调仓再平衡

### 📈 技术分析
- **TA-Lib 集成**: 150+ 技术指标
- **自定义指标**: 支持用户自定义指标
- **多周期分析**: 支持分钟、小时、日线等多周期

### 🔧 工具系统
- **交易工具**: 下单、撤单、查询
- **数据工具**: 行情、历史数据、财务数据
- **风控工具**: 风险检查、止损止盈
- **审计日志**: 完整的操作审计

### 🛡️ 风险控制
- **仓位管理**: 单票仓位、总仓位限制
- **止损止盈**: 动态止损、移动止盈
- **风险指标**: VaR、最大回撤、波动率
- **权限管理**: 操作权限、金额限制

### 📊 数据支持
- **Tushare**: A 股行情、财务数据
- **AkShare**: 免费数据源
- **yfinance**: 美股、全球市场
- **腾讯财经**: 实时行情

### 🖥️ 可视化
- **Streamlit 看板**: 多页面交互式看板
- **Plotly Dash**: 实时监控看板
- **绩效分析**: 收益曲线、风险指标
- **持仓分析**: 持仓分布、盈亏分析

### ⚙️ 配置系统
- **5 层继承**: Global → Strategy → Channel → Account → Group
- **SecretRef**: 安全的密钥管理
- **JSON5**: 支持注释的配置文件
- **自动迁移**: 配置版本迁移

---

## 📁 项目结构

```
bobquant/
├── core/                    # 核心模块
│   ├── account.py          # 账户管理
│   ├── executor.py         # 订单执行器
│   └── risk_filters.py     # 风控过滤器
│
├── strategy/               # 策略模块
│   ├── engine.py          # 策略引擎
│   ├── multi_factor.py    # 多因子策略
│   ├── grid_t_v2_5_patch.py # 网格 T 策略
│   ├── high_frequency.py  # 高频策略
│   └── rebalance.py       # 再平衡策略
│
├── data/                   # 数据模块
│   ├── provider.py        # 数据源抽象
│   ├── tushare_provider.py # Tushare 数据源
│   ├── akshare_provider.py # AkShare 数据源
│   └── yfinance_provider.py # yfinance 数据源
│
├── indicator/              # 指标模块
│   ├── technical.py       # 技术指标
│   └── talib_advanced.py  # TA-Lib 高级用法
│
├── tools/                  # 工具系统
│   ├── base.py            # 工具基类
│   ├── registry.py        # 工具注册表
│   ├── schema.py          # Schema 验证
│   ├── audit.py           # 审计日志
│   ├── trading/           # 交易工具
│   ├── data/              # 数据工具
│   └── risk/              # 风控工具
│
├── config/                 # 配置系统
│   ├── schema.py          # Pydantic Schema
│   ├── migrations.py      # 配置迁移
│   └── settings.json5     # 配置文件
│
├── backtest/               # 回测模块
│   ├── vectorbt_backtest.py # VectorBT 回测
│   └── backtrader_integration.py # Backtrader 集成
│
├── web/                    # Web 模块
│   ├── streamlit_app.py   # Streamlit 应用
│   ├── dashboard.py       # Dash 看板
│   └── index.html         # 统一导航页
│
├── ml/                     # 机器学习
│   ├── feature_engineering.py # 特征工程
│   └── ml_strategy.py     # ML 策略
│
├── rl/                     # 强化学习
│   └── rl_integration.py  # RL 集成
│
├── optimize/               # 优化模块
│   └── optuna_optimizer.py # Optuna 优化
│
├── event/                  # 事件系统
│   └── event_engine.py    # 事件引擎
│
├── notify/                 # 通知模块
│   └── feishu_notifier.py # 飞书通知
│
├── permissions/            # 权限管理
│   └── permission_engine.py # 权限引擎
│
├── telemetry/              # 遥测模块
│   └── metrics.py         # 监控指标
│
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖列表
└── README.md              # 本文档
```

---

## 🔧 系统要求

### 最低要求
- **Python**: 3.10+
- **内存**: 4GB+
- **磁盘**: 1GB+
- **网络**: 稳定互联网连接

### 推荐配置
- **Python**: 3.11+
- **内存**: 8GB+
- **磁盘**: 10GB+ (含历史数据)
- **网络**: 低延迟网络

### 依赖库
```bash
# 核心依赖
pandas>=2.0.0
numpy>=1.24.0
pydantic>=2.0.0
requests>=2.31.0

# 技术分析
ta-lib>=0.4.24
pandas-ta>=0.3.14b

# 回测
vectorbt>=0.26.0
backtrader>=1.9.78

# 机器学习
scikit-learn>=1.3.0
xgboost>=2.0.0

# 优化
optuna>=3.4.0

# Web
streamlit>=1.30.0
plotly>=5.18.0
dash>=2.14.0

# 数据源
tushare>=1.2.89
akshare>=1.12.0
yfinance>=0.2.31

# 其他
json5>=0.9.14
python-dotenv>=1.0.0
```

---

## 🚀 使用场景

### 1. 策略开发
```python
from bobquant.strategy import Strategy

class MyStrategy(Strategy):
    def on_bar(self, bar):
        # 实现你的策略逻辑
        if self.should_buy(bar):
            self.buy(symbol=bar.symbol, quantity=100)
        elif self.should_sell(bar):
            self.sell(symbol=bar.symbol, quantity=100)
```

### 2. 回测
```python
from bobquant.backtest import BacktestEngine

engine = BacktestEngine(
    strategy=MyStrategy(),
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=1000000
)

results = engine.run()
print(results.summary())
```

### 3. 实盘交易
```python
from bobquant.core import TradingEngine

engine = TradingEngine(mode="live")
engine.start()
```

### 4. 数据分析
```python
from bobquant.data import get_market_data

df = get_market_data("600519.SH", start="2023-01-01")
print(df.head())
```

### 5. 风险控制
```python
from bobquant.tools import risk_check

result = risk_check(
    symbol="600519",
    quantity=1000,
    account_id="account_001"
)
print(result)
```

---

## 📊 性能指标

### 回测性能
- **回测速度**: 10 年日线数据 < 1 秒 (VectorBT)
- **支持频率**: 1 分钟 ~ 月线
- **股票数量**: 支持全市场 5000+ 股票

### 实盘性能
- **订单延迟**: < 100ms
- **数据刷新**: 3 秒 (Dash) / 30 秒 (Streamlit)
- **并发处理**: 支持多策略并行

---

## 🤝 贡献指南

欢迎贡献代码、文档或提出建议！

1. Fork 仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](../LICENSE) 文件了解详情。

---

## 📞 联系方式

- **GitHub**: [@davidsun18](https://github.com/davidsun18)
- **问题反馈**: [GitHub Issues](https://github.com/davidsun18/bobquant/issues)

---

## 🙏 致谢

感谢以下开源项目：
- [TA-Lib](https://github.com/ta-lib/ta-lib) - 技术指标库
- [VectorBT](https://github.com/polakowo/vectorbt) - 回测框架
- [Streamlit](https://streamlit.io/) - Web 框架
- [Optuna](https://optuna.org/) - 参数优化
- [Tushare](https://tushare.pro/) - 数据源
- [AkShare](https://akshare.akfamily.xyz/) - 数据源

---

**最后更新**: 2026-04-11  
**版本**: v3.0  
**状态**: ✅ 活跃维护中
