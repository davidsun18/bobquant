# BobQuant 迁移常见问题解答 (FAQ)

**版本**: v1.0  
**创建时间**: 2026-04-11  
**用途**: 解答迁移过程中的常见问题

---

## 目录

1. [环境准备](#1-环境准备)
2. [配置迁移](#2-配置迁移)
3. [代码迁移](#3-代码迁移)
4. [数据迁移](#4-数据迁移)
5. [策略相关](#5-策略相关)
6. [风险管理](#6-风险管理)
7. [订单执行](#7-订单执行)
8. [回测验证](#8-回测验证)
9. [UI 看板](#9-ui-看板)
10. [性能优化](#10-性能优化)
11. [故障排查](#11-故障排查)

---

## 1. 环境准备

### Q1: Python 版本要求是什么？

**A**: v2.x 要求 Python 3.8 或更高版本。

```bash
# 检查 Python 版本
python3 --version

# 如果版本过低，升级 Python
# Ubuntu/Debian
sudo apt update
sudo apt install python3.9

# macOS
brew install python@3.9
```

### Q2: 如何安装依赖包？

**A**: 使用 requirements.txt 安装。

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
pip3 install -r requirements.txt

# 验证安装
python3 -c "import pandas; import numpy; print('✅ 依赖安装成功')"
```

### Q3: 遇到依赖冲突怎么办？

**A**: 创建虚拟环境。

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 如果仍有冲突，尝试升级 pip
pip install --upgrade pip
pip install -r requirements.txt
```

### Q4: 磁盘空间需要多少？

**A**: 建议至少 5GB 可用空间。

```bash
# 检查磁盘空间
df -h

# 清理空间（如果需要）
rm -rf __pycache__
rm -rf .pytest_cache
rm -f *.log
```

---

## 2. 配置迁移

### Q5: 配置文件放在哪里？

**A**: v2.x 使用 `config/` 目录。

```
bobquant/
└── config/
    ├── settings.yaml      # 系统配置
    ├── stock_pool.yaml    # 股票池配置
    └── backtest.yaml      # 回测配置
```

### Q6: 如何从 v1.x 配置迁移到 v2.x？

**A**: 参考以下映射：

| v1.x 配置 | v2.x 配置位置 |
|----------|-------------|
| MACD_SHORT | `strategy.signal.dual_macd_short[0]` |
| MACD_LONG | `strategy.signal.dual_macd_long[0]` |
| STOP_LOSS | `risk_management.limits.max_daily_loss` |
| STOCKS | `stock_pool.sectors.*.stocks` |

### Q7: YAML 配置语法错误怎么办？

**A**: 使用 YAML 验证工具。

```bash
# 安装 yamllint
pip install yamllint

# 验证配置
yamllint config/settings.yaml
yamllint config/stock_pool.yaml

# 或使用 Python 验证
python3 -c "import yaml; yaml.safe_load(open('config/settings.yaml'))"
```

### Q8: 如何备份配置？

**A**: 使用以下命令：

```bash
# 备份所有配置
cp config/settings.yaml config/settings_backup_$(date +%Y%m%d).yaml
cp config/stock_pool.yaml config/stock_pool_backup_$(date +%Y%m%d).yaml

# 恢复配置
cp config/settings_backup_20260411.yaml config/settings.yaml
```

---

## 3. 代码迁移

### Q9: 如何迁移自定义策略？

**A**: 遵循以下步骤：

1. 在 `strategy/` 目录创建新文件
2. 继承 `BaseStrategy` 基类
3. 实现 `generate_signal()` 方法
4. 在配置中注册

```python
# strategy/my_strategy.py
from bobquant.strategy.base import BaseStrategy

class MyStrategy(BaseStrategy):
    def generate_signal(self, df):
        # 你的策略逻辑
        return {'action': 'buy', 'confidence': 0.8}
```

```yaml
# config/settings.yaml
strategy:
  name: "my_strategy"  # 使用你的策略
```

### Q10: 旧代码还能用吗？

**A**: v2.x 提供兼容层，但建议尽快迁移。

```python
# 兼容层（临时使用）
from bobquant.compat.v1 import get_data, buy, sell

# 但建议迁移到新 API
from bobquant.data.provider import DataProvider
from bobquant.core.executor import OrderExecutor
```

### Q11: 如何处理导入错误？

**A**: 检查模块路径。

```bash
# 常见导入错误及解决方案

# 错误：ModuleNotFoundError: No module named 'bobquant'
# 解决：添加项目路径
export PYTHONPATH=/home/openclaw/.openclaw/workspace/quant_strategies:$PYTHONPATH

# 错误：ImportError: cannot import name 'xxx'
# 解决：检查模块是否存在
python3 -c "from bobquant.core import account; print('OK')"
```

### Q12: 代码迁移后报错怎么办？

**A**: 逐步排查：

1. 检查错误信息
2. 查看日志文件
3. 验证数据类型
4. 对比新旧代码差异

```bash
# 查看详细错误
python3 main.py 2>&1 | tee error.log

# 查看日志
tail -f logs/bobquant.log
```

---

## 4. 数据迁移

### Q13: 历史数据需要迁移吗？

**A**: 是的，但 v2.x 会自动适配旧格式。

```bash
# 备份旧数据
cp -r data/ data_backup/

# v2.x 会自动识别以下格式
# - v1.x 格式：date, open, high, low, close, volume
# - v2.x 格式：trade_date, open, high, low, close, vol, amount
```

### Q14: 如何切换数据源？

**A**: 修改配置文件。

```yaml
# config/settings.yaml
data:
  primary_source: "tushare"  # 或 'tencent', 'akshare'
```

```python
# 或在代码中切换
from bobquant.data.provider import DataProvider

provider = DataProvider(source='tushare', token='your_token')
df = provider.get_history_data('601398', days=60)
```

### Q15: 数据获取失败怎么办？

**A**: 检查以下项目：

```bash
# 1. 检查网络连接
ping www.gtimg.cn
ping api.tushare.pro

# 2. 测试数据接口
python3 data/test_akshare.py
python3 data/test_tushare.py

# 3. 检查数据源配置
cat config/settings.yaml | grep primary_source

# 4. 清除缓存
rm -rf data/cache/*
```

### Q16: 数据格式不一致怎么办？

**A**: v2.x 提供格式转换。

```python
from bobquant.data.utils import convert_to_v2_format

# 转换旧格式数据
df_old = pd.read_csv('old_data.csv')
df_new = convert_to_v2_format(df_old)
df_new.to_csv('new_data.csv')
```

---

## 5. 策略相关

### Q17: 双 MACD 如何工作？

**A**: 双 MACD 使用两个周期的 MACD 进行确认。

```python
# 短周期 MACD (6,13,5) - 敏感
# 长周期 MACD (24,52,18) - 稳定

# 只有当两个 MACD 同时金叉/死叉时，才认为是有效信号
# 这减少了假信号，提升胜率约 10-15%
```

### Q18: 如何调整双 MACD 参数？

**A**: 修改配置文件。

```yaml
# config/settings.yaml
strategy:
  signal:
    dual_macd_short: [6, 13, 5]    # 短周期参数
    dual_macd_long: [24, 52, 18]   # 长周期参数
```

### Q19: 动态布林带是什么？

**A**: 根据波动率自适应调整标准差倍数。

- 高波动股票：2.5 倍标准差（放宽）
- 低波动股票：1.8 倍标准差（收紧）
- 中等波动：2.0 倍标准差（标准）

### Q20: 策略信号不准确怎么办？

**A**: 调整策略参数。

```yaml
# config/settings.yaml
strategy:
  signal:
    # 调整 MACD 参数
    dual_macd_short: [8, 17, 7]   # 更不敏感
    dual_macd_long: [30, 60, 20]  # 更稳定
    
    # 调整布林带参数
    bollinger_std_high: 2.8       # 更宽
    bollinger_std_low: 1.5        # 更窄
```

### Q21: 如何测试新策略？

**A**: 使用回测系统。

```bash
# 运行回测
python3 backtest/run_backtest.py my_strategy 2024-01-01 2024-12-31

# 查看回测报告
cat backtest_results/my_strategy_2024_report.json
```

---

## 6. 风险管理

### Q22: 风控系统频繁拦截订单怎么办？

**A**: 调整风控参数。

```yaml
# config/settings.yaml
risk_management:
  limits:
    max_position_value: 800000    # 提高单笔限额（原 500000）
    max_daily_loss: 80000         # 提高日亏损限额（原 50000）
    max_drawdown: 0.15            # 提高最大回撤（原 0.10）
```

### Q23: 如何查看风控拦截日志？

**A**: 检查日志文件。

```bash
# 查看风控日志
grep "风控拦截" logs/bobquant.log

# 或实时查看
tail -f logs/bobquant.log | grep "风控"
```

### Q24: 如何禁用某项风控检查？

**A**: 修改配置（不推荐）。

```yaml
# config/settings.yaml
risk_management:
  filters:
    enabled: false  # 禁用所有过滤器（危险！）
  
  # 或禁用特定检查
  market_risk:
    enabled: false  # 禁用大盘风控
```

### Q25: 回撤超限后如何恢复？

**A**: 系统会自动停止交易，需要手动重置。

```python
# 重置风控状态
from bobquant.risk_management.risk_manager import RiskManager

risk_mgr.reset_daily()  # 重置每日状态
risk_mgr.peak_capital = risk_mgr.current_capital  # 重置峰值
```

---

## 7. 订单执行

### Q26: TWAP 如何工作？

**A**: TWAP 将大单拆分为小单，按时间均匀执行。

```yaml
# config/settings.yaml
execution:
  use_twap: true
  twap_threshold: 10000        # 大于 10000 股使用 TWAP
  twap_duration_minutes: 10    # 执行时长 10 分钟
  twap_slices: 5               # 拆分为 5 份
```

### Q27: TWAP 执行效果不佳怎么办？

**A**: 优化 TWAP 参数。

```yaml
# config/settings.yaml
execution:
  twap_threshold: 5000         # 降低触发阈值
  twap_duration_minutes: 15    # 延长执行时间
  twap_slices: 10              # 增加拆分份数
```

### Q28: 如何查看订单执行状态？

**A**: 检查交易日志。

```bash
# 查看执行日志
grep "订单执行" logs/bobquant.log

# 查看 TWAP 订单
grep "TWAP" logs/bobquant.log
```

### Q29: 订单执行失败怎么办？

**A**: 检查以下项目：

1. 风控检查是否通过
2. 可用资金是否充足
3. 股票是否停牌
4. 价格是否合理

```bash
# 查看失败原因
grep "订单失败" logs/bobquant.log
```

---

## 8. 回测验证

### Q30: 如何运行回测？

**A**: 使用回测脚本。

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant

# 回测双 MACD 策略
python3 backtest/run_backtest.py dual_macd 2024-01-01 2024-12-31

# 回测布林带策略
python3 backtest/run_backtest.py bollinger 2024-01-01 2024-12-31
```

### Q31: 回测结果不理想怎么办？

**A**: 调整策略参数或股票池。

```yaml
# 调整策略参数
strategy:
  signal:
    dual_macd_short: [8, 17, 7]
    dual_macd_long: [30, 60, 20]

# 调整股票池
stock_pool:
  sectors:
    tech_semiconductor:
      stocks:
        - {code: "688981", strategy: "bollinger"}  # 改用布林带
```

### Q32: 回测指标含义是什么？

**A**: 关键指标说明：

| 指标 | 含义 | 目标值 |
|------|------|--------|
| 总收益率 | 回测期间总收益 | > 20% |
| 年化收益率 | 年化收益 | > 15% |
| 最大回撤 | 最大亏损幅度 | < 25% |
| 夏普比率 | 风险调整后收益 | > 1.2 |
| 胜率 | 盈利交易占比 | > 55% |

### Q33: 回测与实盘差异大怎么办？

**A**: 考虑以下因素：

1. 滑点设置是否合理（建议 0.2%）
2. 手续费是否正确（建议万三）
3. 数据是否使用复权
4. 市场冲击成本（大单使用 TWAP）

```yaml
# backtest/config.yaml
backtest:
  commission_rate: 0.0003  # 万三手续费
  slippage: 0.002          # 0.2% 滑点
  use_adjusted_price: true # 使用复权价格
```

---

## 9. UI 看板

### Q34: 如何启动 Streamlit 看板？

**A**: 使用启动脚本。

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
./start_streamlit.sh

# 访问 http://localhost:8501
```

### Q35: Streamlit 看板无法访问怎么办？

**A**: 检查服务状态。

```bash
# 检查进程
ps aux | grep streamlit

# 检查端口
netstat -tlnp | grep 8501

# 查看日志
tail -f /tmp/streamlit.log

# 重启服务
pkill -f "streamlit run"
./start_streamlit.sh
```

### Q36: 看板数据显示不正确怎么办？

**A**: 检查数据文件。

```bash
# 检查账户文件
cat logs/account.json

# 检查交易记录
cat logs/trades.json

# 刷新缓存
# 在看板中点击"清除缓存"按钮
```

### Q37: 如何同时使用 Streamlit 和 Dash？

**A**: 两者可以并行运行。

```bash
# Streamlit (端口 8501)
./start_streamlit.sh

# Dash (端口 8050)
python3 web/dash_app.py

# 或使用统一导航页 (端口 8502)
./start_nav_page.sh
```

---

## 10. 性能优化

### Q38: 系统运行缓慢怎么办？

**A**: 优化以下配置：

```yaml
# config/settings.yaml
data:
  cache_enabled: true      # 启用缓存
  cache_ttl_hours: 24      # 缓存 24 小时

logging:
  level: "WARNING"         # 减少日志输出
```

### Q39: 内存占用过高怎么办？

**A**: 优化数据处理。

```python
# 使用分块读取
df = pd.read_csv('data.csv', chunksize=10000)

# 及时释放内存
del df
import gc
gc.collect()
```

### Q40: CPU 使用率过高怎么办？

**A**: 优化计算逻辑。

```yaml
# config/settings.yaml
# 减少刷新频率
strategy:
  update_interval_seconds: 300  # 5 分钟更新一次
```

---

## 11. 故障排查

### Q41: 系统无法启动怎么办？

**A**: 逐步排查：

```bash
# 1. 检查 Python 版本
python3 --version

# 2. 检查依赖
pip3 list | grep -E "pandas|numpy|yaml"

# 3. 检查配置文件
python3 -c "import yaml; yaml.safe_load(open('config/settings.yaml'))"

# 4. 检查导入
python3 -c "from bobquant.core import account"

# 5. 查看详细错误
python3 main.py 2>&1 | tee startup.log
```

### Q42: 日志文件在哪里？

**A**: 日志位置：

- 系统日志：`logs/bobquant.log`
- 交易日志：`sim_trading/模拟盘日志.log`
- Streamlit 日志：`/tmp/streamlit.log`
- 回测日志：`backtest_results/*.log`

### Q43: 如何启用调试模式？

**A**: 修改日志级别。

```yaml
# config/settings.yaml
logging:
  level: "DEBUG"  # DEBUG, INFO, WARNING, ERROR
```

### Q44: 如何生成诊断报告？

**A**: 使用诊断脚本。

```bash
# 生成诊断报告
python3 tools/diagnose.py > diagnosis_$(date +%Y%m%d).txt

# 查看报告
cat diagnosis_20260411.txt
```

### Q45: 遇到问题如何寻求帮助？

**A**: 提供以下信息：

1. 错误信息（完整堆栈）
2. 配置文件（脱敏后）
3. 日志文件（相关部分）
4. 复现步骤

```bash
# 收集诊断信息
python3 tools/collect_diagnostic_info.py

# 这会生成一个包含所有必要信息的压缩包
```

---

## 快速参考

### 常用命令

```bash
# 启动系统
./start_v2.sh

# 启动模拟盘
./start_sim_v2_2.sh

# 启动 Streamlit
./start_streamlit.sh

# 运行回测
python3 backtest/run_backtest.py dual_macd 2024-01-01 2024-12-31

# 查看日志
tail -f logs/bobquant.log

# 检查进程
ps aux | grep bobquant

# 停止服务
pkill -f "python3.*main.py"
pkill -f "streamlit run"
```

### 配置文件位置

```
config/
├── settings.yaml      # 系统配置
├── stock_pool.yaml    # 股票池
└── backtest.yaml      # 回测配置
```

### 日志文件位置

```
logs/
├── bobquant.log           # 系统日志
├── trades.json            # 交易记录
└── account.json           # 账户信息
```

### 重要目录

```
bobquant/
├── core/              # 核心模块
├── strategy/          # 策略引擎
├── indicator/         # 技术指标
├── data/              # 数据接口
├── ml/                # 机器学习
├── backtest/          # 回测系统
├── risk_management/   # 风险管理
├── order_execution/   # 订单执行
└── web/               # UI 界面
```

---

## 附录

### A. 版本兼容性

| 功能 | v1.x | v2.x | 说明 |
|------|------|------|------|
| Python 3.6 | ✅ | ❌ | v2.x 不支持 |
| Python 3.8+ | ✅ | ✅ | 推荐版本 |
| 单 MACD | ✅ | ✅ | 向后兼容 |
| 双 MACD | ❌ | ✅ | 新增功能 |
| 简单风控 | ✅ | ✅ | 向后兼容 |
| 综合风控 | ❌ | ✅ | 新增功能 |
| 市价单 | ✅ | ✅ | 向后兼容 |
| TWAP | ❌ | ✅ | 新增功能 |

### B. 配置参数参考值

```yaml
# 双 MACD 参数
dual_macd_short: [6, 13, 5]     # 短周期（敏感）
dual_macd_long: [24, 52, 18]    # 长周期（稳定）

# 布林带参数
bollinger_std_high: 2.5         # 高波动
bollinger_std_low: 1.8          # 低波动

# 风控参数
max_position_value: 500000      # 单笔最大金额
max_drawdown: 0.10              # 最大回撤 10%
max_daily_loss: 50000           # 单日最大亏损

# TWAP 参数
twap_threshold: 10000           # 触发阈值（股）
twap_duration_minutes: 10       # 执行时长
twap_slices: 5                  # 拆分份数
```

### C. 性能指标目标

| 指标 | 目标值 | 验收标准 |
|------|--------|---------|
| 数据获取响应 | < 500ms | 腾讯财经 API |
| 信号生成时间 | < 100ms | 单只股票 |
| 风控检查时间 | < 50ms | 单次检查 |
| 回测速度 | < 30 秒 | 1 年数据 |
| 内存占用 | < 500MB | 正常运行 |

---

**最后更新**: 2026-04-11  
**维护者**: BobQuant Team  
**反馈**: 如有问题，请查看日志或联系技术支持
