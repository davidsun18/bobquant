# TWAP 执行器使用指南

## 概述

TWAP（时间加权平均价格）执行器已集成到 BobQuant 交易系统，用于将大单拆分为多个小单，按时间均匀执行，减少市场冲击。

## 配置

在 `bobquant/config/settings.yaml` 中添加以下配置：

```yaml
# --- TWAP 算法执行 ---
twap:
  enabled: false                    # 是否启用 TWAP 大单拆分
  threshold: 10000                  # 触发 TWAP 的股数阈值（>10000 股自动拆分）
  slices: 5                         # 拆分份数
  duration_minutes: 10              # 执行时长（分钟）
```

### 配置说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `enabled` | `false` | 是否启用 TWAP 功能 |
| `threshold` | `10000` | 触发 TWAP 的股数阈值，超过此值自动拆分 |
| `slices` | `5` | 将订单拆分为多少份 |
| `duration_minutes` | `10` | 执行总时长（分钟） |

## 自动触发

当启用 TWAP 后，所有超过阈值的订单会自动拆分：

```python
# 在 main.py 中自动初始化
executor = Executor(
    account, 
    s.commission_rate, 
    s.trade_log_file, 
    _log, 
    _notify,
    twap_enabled=s.get('twap.enabled', False),
    twap_threshold=s.get('twap.threshold', 10000),
    twap_slices=s.get('twap.slices', 5),
    twap_duration=s.get('twap.duration_minutes', 10)
)

# 大单自动拆分（>10000 股）
executor.buy('000001.SZ', '平安银行', 15000, 10.5, '策略买入')
# 输出：
# 🔄 TWAP 买入 平安银行：15000 股 → 拆分为 5 份
#    每份：约 3000 股，间隔：2.0 分钟
# 🔴 买入 平安银行：3000 股 @ ¥10.50 [TWAP 1/5]
# 🔴 买入 平安银行：3000 股 @ ¥10.50 [TWAP 2/5]
# ...
```

## 手动控制

可以通过 `use_twap` 参数手动控制是否使用 TWAP：

```python
# 小单但强制使用 TWAP
executor.buy('000001.SZ', '平安银行', 5000, 10.5, '测试', use_twap=True)

# 大单但禁用 TWAP（一次性执行）
executor.buy('000001.SZ', '平安银行', 20000, 10.5, '测试', use_twap=False)
```

## 执行流程

### 买入订单

1. 检查是否启用 TWAP 且股数 ≥ 阈值
2. 计算每份数量：`slice_qty = total_qty // num_slices`
3. 计算时间间隔：`interval = duration / num_slices`
4. 按时间顺序执行每个切片
5. 记录每个切片的成交情况

### 卖出订单

与买入类似，但会考虑持仓限制和 T+1 规则。

## 示例输出

```
============================================================
TWAP 执行器演示
============================================================
✅ TWAP 订单已提交:
   订单 ID: TWAP_081358_774676
   标的：000001.SZ
   方向：buy
   总量：10000
   拆分：5 份
   时长：5 分钟
   每份：约 2000 股

⏳ 开始执行...
  ✓ 执行切片 1/5: 2000 @ 10.57
  ✓ 执行切片 2/5: 2000 @ 10.58
  ✓ 执行切片 3/5: 2000 @ 10.56
  ✓ 执行切片 4/5: 2000 @ 10.59
  ✓ 执行切片 5/5: 2000 @ 10.57

🎉 TWAP 订单完成：TWAP_081358_774676
   总成交：10000 股
   平均价：10.57
   总金额：105,700.00
   执行时长：300.0 秒
```

## 测试

运行测试验证功能：

```bash
# 独立 TWAP 执行器测试
cd /home/openclaw/.openclaw/workspace/quant_strategies
python3 order_execution/twap_executor.py --demo

# 集成测试
python3 bobquant/tests/test_twap_integration.py
```

## 与现有流程兼容

TWAP 执行器完全兼容现有的交易流程：

- ✅ 交易标识符系统（A→B 转换）
- ✅ 板块规则（主板/创业板/科创板）
- ✅ 手续费计算
- ✅ 持仓管理
- ✅ 交易记录同步
- ✅ 飞书通知

## 注意事项

1. **模拟盘 vs 实盘**：当前实现中，所有切片立即执行（模拟环境）。实盘部署时需要：
   - 实现定时检查机制
   - 调用 `twap_executor.check_and_execute_pending()` 执行到期切片

2. **订单状态跟踪**：每个 TWAP 订单都有唯一的 `twap_order_id`，可以通过 `executor.twap_executor.get_active_orders()` 查看活跃订单。

3. **部分成交**：如果某个切片未成交，会保留为 pending 状态，下次检查时重试。

## 文件清单

集成涉及的文件：

```
bobquant/
├── core/
│   └── executor.py              # 主执行器（已集成 TWAPExecutor）
├── config/
│   └── settings.yaml            # 添加 twap 配置项
├── tests/
│   └── test_twap_integration.py # 集成测试
└── main.py                      # 初始化时传入 TWAP 参数

order_execution/
└── twap_executor.py             # 独立 TWAP/VWAP 执行器（QuantConnect 算法）
```

## 未来扩展

- [ ] VWAP（成交量加权平均价格）集成
- [ ] 实盘定时执行机制
- [ ] 订单执行进度可视化
- [ ] 执行质量分析（滑点统计）
