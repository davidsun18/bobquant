# -*- coding: utf-8 -*-
"""
快速测试 AkShare 数据源
"""
import sys
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies/bobquant')

from data.akshare_provider import AkShareProvider
import time

print("=" * 60)
print("AkShare 数据源快速测试")
print("=" * 60)

provider = AkShareProvider(retry=2, delay=0.5)

# 测试 5 只股票
test_stocks = [
    ('sh600519', '贵州茅台'),
    ('sz000001', '平安银行'),
    ('sh601318', '中国平安'),
    ('sz000002', '万科 A'),
    ('sh600036', '招商银行'),
]

print("\n1. 测试实时行情获取 (get_quote)")
print("-" * 60)
results = []
for code, name in test_stocks:
    print(f"获取 {name} ({code})...", end=" ")
    quote = provider.get_quote(code)
    if quote:
        print(f"✓ {quote['current']:.2f}元 ({quote['change']:+.2f}%)")
        results.append((code, name, quote))
    else:
        print("✗ 失败")
    time.sleep(0.3)

print("\n\n2. 测试批量获取 (get_quotes)")
print("-" * 60)
codes = [code for code, _ in test_stocks]
print(f"批量获取 {len(codes)} 只股票...")
quotes = provider.get_quotes(codes)
for code, quote in quotes.items():
    if quote:
        print(f"  ✓ {code}: {quote['current']:.2f}元 ({quote['change']:+.2f}%)")

print("\n\n3. 测试历史数据 (get_history)")
print("-" * 60)
code, name = test_stocks[0]
print(f"获取 {name} ({code}) 最近 5 天历史数据...")
df = provider.get_history(code, days=5)
if df is not None and not df.empty:
    print(f"  ✓ 获取成功，共 {len(df)} 条记录")
    print(f"  ✓ 日期范围：{df.index[0].strftime('%Y-%m-%d')} 至 {df.index[-1].strftime('%Y-%m-%d')}")
    print(f"  ✓ 收盘价：{df['close'].iloc[-1]:.2f}元")
else:
    print("  ✗ 获取失败")

print("\n\n4. 测试财务数据 (get_financial_data)")
print("-" * 60)
code, name = test_stocks[0]
print(f"获取 {name} ({code}) 财务数据...")
financial = provider.get_financial_data(code)
if financial:
    print(f"  ✓ 市盈率 (PE): {financial.get('pe', 'N/A')}")
    print(f"  ✓ 市净率 (PB): {financial.get('pb', 'N/A')}")
    print(f"  ✓ 每股收益 (EPS): {financial.get('eps', 'N/A')}")
else:
    print("  ✗ 获取失败")

print("\n\n5. 测试资金流向 (get_money_flow)")
print("-" * 60)
code, name = test_stocks[0]
print(f"获取 {name} ({code}) 资金流向...")
flow = provider.get_money_flow(code, days=5)
if flow is not None and not flow.empty:
    print(f"  ✓ 获取成功，共 {len(flow)} 条记录")
else:
    print("  ✗ 获取失败")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)

# 输出总结
print("\n【测试结果总结】")
print(f"  - 实时行情：{len(results)}/{len(test_stocks)} 成功")
print(f"  - 批量获取：{len(quotes)}/{len(codes)} 成功")
print(f"  - 历史数据：{'成功' if df is not None else '失败'}")
print(f"  - 财务数据：{'成功' if financial else '失败'}")
print(f"  - 资金流向：{'成功' if flow is not None else '失败'}")
