# 做 T 策略问题分析和解决方案

## 🔍 问题根源

**当前网格策略限制条件太多**：

1. ❌ 股价在 5 日均线上方 2% → 不做 T（强势股不做）
2. ❌ RSI < 65 → 不做 T（未超买不做）
3. ❌ t_grid_up 默认 0.03 (3%) → 阈值太高
4. ❌ t_grid_max 默认 3 层 → 层数太少
5. ❌ 单次卖出 50% 仓位 → 太粗

## ✅ 解决方案

### 方案 1: 修改 GridTStrategy.check_sell()

**删除趋势判断**，只保留基础逻辑：

```python
def check_sell(self, code, quote, sellable, df=None):
    """v2.5 超灵敏版：只要有波动就做 T"""
    if sellable <= 0 or quote['open'] <= 0:
        return 0, ''
    
    # 检查交易时段
    from datetime import datetime
    now = datetime.now()
    current_time = now.strftime('%H:%M')
    is_morning = '09:30' <= current_time <= '11:30'
    is_afternoon = '13:00' <= current_time <= '15:00'
    
    if not (is_morning or is_afternoon):
        return 0, ''
    
    # 计算日内涨幅
    intraday = (quote['current'] - quote['open']) / quote['open']
    info = self._state.get(code, {'sells': [], 'total_sold': 0, 'count': 0, 'bought_back': False})

    if info['bought_back'] or info['count'] >= self.config.get('t_grid_max', 12):
        return 0, ''

    target_level = info['count'] + 1
    # v2.5: 0.1% + (层数 -1)*0.05%
    trigger = self.config.get('t_grid_up', 0.001) + (target_level - 1) * self.config.get('t_grid_step', 0.0005)

    if intraday >= trigger:
        sell_ratio = self.config.get('t_sell_ratio', 0.2)  # 20% 仓位
        shares = int(sellable * sell_ratio / 100) * 100
        shares = max(shares, 100)  # 最小 100 股
        if shares >= 100:
            return shares, f'网格做 T L{target_level} (日内 +{intraday*100:.2f}%)'
    
    return 0, ''
```

### 方案 2: 改用相对成本价的做 T 策略

**基于持仓成本**而不是开盘价：

```python
def check_sell_v2(self, code, quote, sellable, pos, df=None):
    """v2.5: 基于持仓成本的做 T 策略"""
    if sellable <= 0 or not pos:
        return 0, ''
    
    avg_cost = pos.get('avg_price', quote['current'])
    profit_pct = (quote['current'] - avg_cost) / avg_cost
    
    # 盈利≥0.1% 即可做 T
    if profit_pct >= self.config.get('t_grid_up', 0.001):
        sell_ratio = self.config.get('t_sell_ratio', 0.2)
        shares = int(sellable * sell_ratio / 100) * 100
        return max(shares, 100), f'盈利做 T (+{profit_pct*100:.2f}%)'
    
    return 0, ''
```

## 📋 需要修改的文件

1. `bobquant/strategy/engine.py` - GridTStrategy.check_sell()
2. `bobquant/config/sim_config_v2_4_aggressive.yaml` - 已修改

## 🎯 预期效果

**修改前**：
- 条件：股价≥开盘价 3% + RSI≥65 + 非强势股
- 结果：几乎不触发

**修改后**：
- 条件：股价≥开盘价 0.1%
- 结果：日均 20-40 笔交易

## ⚠️ 注意事项

1. 手续费：日交易 40 笔 ≈ ¥800/日
2. 滑点：快速进出可能有滑点损失
3. 建议：先测试 1 小时，观察实际效果
