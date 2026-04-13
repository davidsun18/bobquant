# BobQuant 快速开始指南

5 分钟上手 BobQuant 量化交易系统。

---

## ⏱️ 5 分钟快速开始

### 第 1 分钟：安装

```bash
# 克隆仓库
git clone https://github.com/davidsun18/bobquant.git
cd bobquant

# 安装依赖
pip install -r requirements.txt
```

### 第 2 分钟：配置

```bash
# 复制配置示例
cp config/config_example.json5 config/settings.json5

# 编辑配置（设置必要的参数）
vim config/settings.json5
```

**最小配置**:
```json5
{
  "system": {
    "name": "BobQuant 模拟盘",
    "mode": "simulation"
  },
  "account": {
    "initial_capital": 1000000
  }
}
```

### 第 3 分钟：启动

```bash
# 启动主程序
python3 main.py

# 或启动模拟盘
./start_sim_v2_2.sh
```

### 第 4 分钟：查看看板

```bash
# 启动 Streamlit 看板
./start_streamlit.sh
```

访问 http://localhost:8501

### 第 5 分钟：运行策略

```python
# 创建简单策略
cat > my_strategy.py << 'EOF'
from bobquant.strategy import Strategy

class MyStrategy(Strategy):
    def on_bar(self, bar):
        # 简单的均线策略
        if bar.close > bar.open:
            print(f"{bar.symbol} 上涨")
        else:
            print(f"{bar.symbol} 下跌")

if __name__ == "__main__":
    from bobquant.core import TradingEngine
    engine = TradingEngine(strategy=MyStrategy())
    engine.start()
EOF

# 运行策略
python3 my_strategy.py
```

---

## 📋 完整安装指南

### 系统要求

- **Python**: 3.10+
- **操作系统**: Linux / macOS / Windows
- **内存**: 4GB+
- **磁盘**: 1GB+

### 安装步骤

#### 1. 安装 Python

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv

# macOS
brew install python@3.11

# Windows
# 从 https://python.org 下载安装
```

#### 2. 创建虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

#### 3. 安装依赖

```bash
# 安装核心依赖
pip install -r requirements.txt

# 或分步安装
pip install pandas numpy pydantic requests
pip install ta-lib vectorbt
pip install streamlit plotly
pip install tushare akshare yfinance
```

#### 4. 安装 TA-Lib (可选但推荐)

```bash
# Ubuntu/Debian
sudo apt install libta-lib-dev

# macOS
brew install ta-lib

# Windows
# 下载预编译包：https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
pip install TA-Lib-0.4.24-cp311-cp311-win_amd64.whl
```

---

## 🔧 配置详解

### 配置文件位置

```
config/
├── settings.json5          # 主配置文件
├── config_example.json5    # 配置示例
└── strategies/             # 策略配置
    ├── conservative.json5  # 保守策略
    ├── aggressive.json5    # 激进策略
    └── balanced.json5      # 平衡策略
```

### 配置结构

```json5
{
  // 系统配置
  "system": {
    "name": "BobQuant 模拟盘",
    "version": "3.0",
    "mode": "simulation",  // "live" | "simulation" | "backtest"
    "log_level": "INFO"
  },
  
  // 账户配置
  "account": {
    "initial_capital": 1000000,  // 初始资金
    "commission_rate": 0.0005,   // 手续费率
    "api_key": "${env:BOBQUANT_API_KEY}"
  },
  
  // 仓位配置
  "position": {
    "max_position_pct": 0.10,    // 单票最大仓位 10%
    "max_total_position": 0.80,  // 总仓位上限 80%
    "max_positions": 10          // 最多持有 10 只股票
  },
  
  // 风控配置
  "risk": {
    "max_drawdown": 0.10,        // 最大回撤 10%
    "daily_loss_limit": 0.03,    // 单日亏损限制 3%
    "var_limit": 0.05            // VaR 限制 5%
  },
  
  // 策略配置
  "strategy": {
    "name": "multi_factor",
    "rebalance_days": 5,         // 5 天调仓一次
    "universe_size": 30          // 股票池大小 30
  },
  
  // 数据配置
  "data": {
    "provider": "tushare",       // 数据源
    "cache_enabled": true,       // 启用缓存
    "cache_days": 7              // 缓存 7 天
  },
  
  // 通知配置
  "notify": {
    "feishu_webhook": "${env:FEISHU_WEBHOOK}",
    "enabled": true
  }
}
```

### SecretRef 使用

```json5
{
  "account": {
    // 方式 1: 环境变量
    "api_key": "${env:BOBQUANT_API_KEY}",
    
    // 方式 2: 文件
    "secret": "${file:~/.bobquant/secret.txt}",
    
    // 方式 3: 命令
    "password": "${cmd:vault read secret/password}"
  }
}
```

### 5 层配置继承

```
优先级从低到高:
1. Global Defaults (全局默认)
2. Per-Strategy (策略级)
3. Per-Channel (渠道级)
4. Per-Account (账户级)
5. Per-Group (组级)
```

**示例**:
```json5
{
  "global_defaults": {
    "position": {"max_position_pct": 0.10}
  },
  
  "strategy_configs": {
    "conservative": {
      "position": {"max_position_pct": 0.05}  // 覆盖为 5%
    }
  },
  
  "account_configs": {
    "account_001": {
      "account": {"initial_capital": 500000}
    }
  }
}
```

---

## 🚀 运行模式

### 模拟盘模式

```bash
# 启动模拟盘
./start_sim_v2_2.sh

# 或手动启动
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
python3 main.py --mode simulation
```

### 实盘模式 (谨慎使用)

```bash
# 启动实盘
python3 main.py --mode live

# 需要配置实盘参数
# config/settings.json5:
# {
#   "system": {"mode": "live"},
#   "account": {"api_key": "xxx", "api_secret": "xxx"}
# }
```

### 回测模式

```python
from bobquant.backtest import BacktestEngine
from bobquant.strategy import MyStrategy

engine = BacktestEngine(
    strategy=MyStrategy(),
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=1000000
)

results = engine.run()
print(results.summary())
```

---

## 📊 使用看板

### Streamlit 看板

```bash
# 启动
./start_streamlit.sh

# 访问
# http://localhost:8501
```

**功能**:
- 📊 账户概览
- 📈 持仓分析
- 📝 交易记录
- 📈 绩效分析
- ⚙️ 设置

### Plotly Dash 看板

```bash
# 启动
python3 web/dashboard.py

# 访问
# http://localhost:8050
```

### 统一导航页

```bash
# 启动
./start_nav_page.sh

# 访问
# http://localhost:8502
```

---

## 💻 开发第一个策略

### 简单均线策略

```python
from bobquant.strategy import Strategy
from bobquant.indicator import MA

class MAStrategy(Strategy):
    """简单均线交叉策略"""
    
    def on_init(self):
        """初始化"""
        self.ma_fast = MA(5)   # 5 日均线
        self.ma_slow = MA(20)  # 20 日均线
        self.position = 0
    
    def on_bar(self, bar):
        """K 线回调"""
        # 更新指标
        self.ma_fast.update(bar.close)
        self.ma_slow.update(bar.close)
        
        # 金叉买入
        if (self.ma_fast.value > self.ma_slow.value and 
            self.position == 0):
            self.buy(bar.symbol, 100)
            self.position = 100
            print(f"买入 {bar.symbol}")
        
        # 死叉卖出
        elif (self.ma_fast.value < self.ma_slow.value and 
              self.position > 0):
            self.sell(bar.symbol, self.position)
            self.position = 0
            print(f"卖出 {bar.symbol}")

# 运行策略
if __name__ == "__main__":
    from bobquant.core import TradingEngine
    
    engine = TradingEngine(
        strategy=MAStrategy(),
        mode="simulation"
    )
    engine.start()
```

### 多因子策略

```python
from bobquant.strategy import MultiFactorStrategy

class MyMFStrategy(MultiFactorStrategy):
    """多因子选股策略"""
    
    def __init__(self):
        super().__init__(
            factors=["momentum", "value", "quality"],
            weights=[0.4, 0.3, 0.3],
            rebalance_days=5
        )
    
    def calculate_factor_score(self, symbol: str) -> float:
        """计算单只股票的因子得分"""
        # 动量因子
        momentum = self.get_momentum(symbol)
        
        # 价值因子
        value = self.get_value(symbol)
        
        # 质量因子
        quality = self.get_quality(symbol)
        
        # 加权得分
        score = (
            momentum * 0.4 +
            value * 0.3 +
            quality * 0.3
        )
        
        return score
```

### 网格 T+0 策略

```python
from bobquant.strategy import GridTStrategy

class MyGridStrategy(GridTStrategy):
    """网格 T+0 策略"""
    
    def __init__(self):
        super().__init__(
            grid_size=0.02,      # 2% 网格
            max_grid=10,         # 10 层网格
            base_quantity=100    # 基础数量 100 股
        )
    
    def on_bar(self, bar):
        """K 线回调"""
        # 自动执行网格交易
        self.execute_grid(bar.symbol, bar.close)
```

---

## 🧪 测试策略

### 回测

```python
from bobquant.backtest import BacktestEngine
from my_strategy import MAStrategy

# 创建回测引擎
engine = BacktestEngine(
    strategy=MAStrategy(),
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=1000000,
    commission_rate=0.0005
)

# 运行回测
results = engine.run()

# 查看结果
print("=" * 50)
print("回测结果")
print("=" * 50)
print(f"总收益：{results.total_return:.2%}")
print(f"年化收益：{results.annual_return:.2%}")
print(f"夏普比率：{results.sharpe_ratio:.2f}")
print(f"最大回撤：{results.max_drawdown:.2%}")
print(f"交易次数：{results.total_trades}")

# 生成报告
results.generate_report("backtest_report.html")
```

### 参数优化

```python
from bobquant.optimize import OptunaOptimizer
from my_strategy import MAStrategy

# 创建优化器
optimizer = OptunaOptimizer(
    strategy_class=MAStrategy,
    start_date="2023-01-01",
    end_date="2023-12-31"
)

# 定义参数空间
param_space = {
    "ma_fast_period": (5, 20),
    "ma_slow_period": (10, 60)
}

# 运行优化
best_params, best_score = optimizer.optimize(
    param_space=param_space,
    n_trials=100,
    objective="sharpe_ratio"  # 优化目标：夏普比率
)

print(f"最优参数：{best_params}")
print(f"最优夏普比率：{best_score:.2f}")
```

---

## 📁 常用命令

### 启动命令

```bash
# 启动主程序
python3 main.py

# 启动模拟盘
./start_sim_v2_2.sh

# 启动回测
python3 backtest/run_backtest.py

# 启动看板
./start_streamlit.sh

# 启动导航页
./start_nav_page.sh
```

### 查看状态

```bash
# 查看进程
ps aux | grep "python3 main.py"

# 查看日志
tail -f logs/bobquant.log

# 查看端口
netstat -tlnp | grep :8501
```

### 停止服务

```bash
# 停止主程序
pkill -f "python3 main.py"

# 停止看板
pkill -f "streamlit run"
```

### 数据管理

```bash
# 清除缓存
rm -rf data/cache/*

# 更新数据
python3 scripts/update_data.py

# 导出数据
python3 scripts/export_data.py
```

---

## 🔍 故障排查

### 常见问题

#### 1. 依赖安装失败

```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 2. TA-Lib 安装失败

```bash
# Ubuntu
sudo apt install libta-lib-dev
pip install ta-lib

# macOS
brew install ta-lib
pip install ta-lib

# Windows
# 下载预编译包安装
```

#### 3. 配置加载失败

```bash
# 检查配置文件
python3 -c "from bobquant.config import ConfigLoader; loader = ConfigLoader('config/settings.json5'); print(loader.load())"

# 验证配置
python3 -c "from bobquant.config import ConfigLoader, ConfigValidator; loader = ConfigLoader('config/settings.json5'); config = loader.load(); validator = ConfigValidator(config); print(validator.validate_all())"
```

#### 4. 数据获取失败

```bash
# 检查数据源
python3 -c "from bobquant.data import get_market_data; df = get_market_data('600519.SH', '1d', '2023-01-01', '2023-01-31'); print(df.head())"

# 检查 Tushare Token
echo $TUSHARE_TOKEN
```

#### 5. 看板无法访问

```bash
# 检查端口
netstat -tlnp | grep :8501

# 检查防火墙
sudo ufw allow 8501

# 查看日志
tail -f /tmp/streamlit.log
```

---

## 📚 下一步

完成快速开始后，你可以：

1. **阅读详细文档**
   - [系统架构](./ARCHITECTURE.md)
   - [API 参考](./API_REFERENCE.md)
   - [最佳实践](./BEST_PRACTICES.md)

2. **学习策略开发**
   - [策略示例](../strategy/EXAMPLES.md)
   - [多因子策略](../backtest/MULTIFRAME_GUIDE.md)
   - [网格 T 策略](../strategy/GRID_T_GUIDE.md)

3. **深入高级功能**
   - [参数优化](../optimize/OPTUNA_INTEGRATION_SUMMARY.md)
   - [机器学习](../ml/README.md)
   - [强化学习](../rl/README.md)

4. **参与社区**
   - [GitHub Issues](https://github.com/davidsun18/bobquant/issues)
   - [讨论区](https://github.com/davidsun18/bobquant/discussions)

---

## 📞 获取帮助

- **文档**: https://github.com/davidsun18/bobquant/tree/main/docs
- **问题**: https://github.com/davidsun18/bobquant/issues
- **讨论**: https://github.com/davidsun18/bobquant/discussions

---

**祝你交易顺利！** 📈

**最后更新**: 2026-04-11
