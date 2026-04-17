# -*- coding: utf-8 -*-
"""
快速验证测试 - AkShare 数据源
测试 5 只股票的基本功能
"""
import sys
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies/bobquant')

from data.akshare_provider import AkShareProvider

print("=" * 70)
print("AkShare 数据源 - 快速验证测试 (5 只股票)")
print("=" * 70)

provider = AkShareProvider(retry=2, delay=0.5)

# 测试 5 只股票
test_stocks = [
    ('sh600519', '贵州茅台'),
    ('sz000001', '平安银行'),
    ('sh601318', '中国平安'),
    ('sz000002', '万科 A'),
    ('sh600036', '招商银行'),
]

results = {
    'quote': 0,
    'history': 0,
    'batch': 0,
}

print("\n[1/3] 测试实时行情 (get_quote)")
print("-" * 70)
for code, name in test_stocks:
    quote = provider.get_quote(code)
    if quote:
        print(f"  ✓ {name} ({code}): {quote['current']:.2f}元 ({quote['change']:+.2f}%)")
        results['quote'] += 1
    else:
        print(f"  ✗ {name} ({code}): 获取失败")

print(f"\n实时行情：{results['quote']}/{len(test_stocks)} 成功")

print("\n[2/3] 测试批量获取 (get_quotes)")
print("-" * 70)
codes = [code for code, _ in test_stocks]
quotes = provider.get_quotes(codes)
for code, quote in quotes.items():
    if quote:
        print(f"  ✓ {code}: {quote['current']:.2f}元")
        results['batch'] += 1

print(f"\n批量获取：{results['batch']}/{len(codes)} 成功")

print("\n[3/3] 测试历史数据 (get_history)")
print("-" * 70)
for code, name in test_stocks[:2]:  # 只测前 2 只节省时间
    df = provider.get_history(code, days=5)
    if df is not None and not df.empty:
        print(f"  ✓ {name} ({code}): {len(df)}条记录，收盘价 {df['close'].iloc[-1]:.2f}元")
        results['history'] += 1
    else:
        print(f"  ✗ {name} ({code}): 获取失败")

print(f"\n历史数据：{results['history']}/2 成功")

# 总结
print("\n" + "=" * 70)
print("测试结果总结")
print("=" * 70)
print(f"  实时行情：{results['quote']}/{len(test_stocks)} ✓")
print(f"  批量获取：{results['batch']}/{len(codes)} ✓")
print(f"  历史数据：{results['history']}/2 ✓")
print()

if results['quote'] >= 3 and results['batch'] >= 3:
    print("【结论】AkShare 数据源集成成功！✓")
else:
    print("【结论】部分功能受限，请检查网络连接")

print("=" * 70)
