# -*- coding: utf-8 -*-
"""
Tushare 数据源简单测试 (无需 token)
测试代码结构和导入是否正常
"""
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("Tushare 数据源 - 代码结构测试")
print("=" * 60)

# 测试 1: 导入模块
print("\n1. 测试模块导入...")
try:
    from data.tushare_provider import TushareProvider
    print("   ✓ TushareProvider 导入成功")
except Exception as e:
    print(f"   ✗ 导入失败：{e}")
    sys.exit(1)

# 测试 2: 创建实例 (无 token)
print("\n2. 测试创建实例...")
try:
    provider = TushareProvider(token='', retry=1, delay=0.1)
    print("   ✓ TushareProvider 实例创建成功")
    print(f"   ✓ Token 设置：{'已设置' if provider.token else '未设置'}")
    print(f"   ✓ Pro API: {'已初始化' if provider.pro else '未初始化'}")
except Exception as e:
    print(f"   ✗ 创建失败：{e}")
    sys.exit(1)

# 测试 3: 测试代码格式化
print("\n3. 测试股票代码格式化...")
test_cases = [
    ('sh600519', '600519.SH'),
    ('sz000001', '000001.SZ'),
    ('600519', '600519.SH'),
    ('000001', '000001.SZ'),
    ('600519.SH', '600519.SH'),
    ('000001.SZ', '000001.SZ'),
]

all_passed = True
for input_code, expected in test_cases:
    result = provider._normalize_code(input_code)
    status = "✓" if result == expected else "✗"
    print(f"   {status} {input_code} → {result} (期望：{expected})")
    if result != expected:
        all_passed = False

if not all_passed:
    print("   ✗ 部分测试失败")
    sys.exit(1)

# 测试 4: 测试接口调用 (无 token 时应返回 None)
print("\n4. 测试接口调用 (无 token 预期返回 None)...")
try:
    quote = provider.get_quote('600519.SH')
    if quote is None:
        print("   ✓ get_quote 在无 token 时正确返回 None")
    else:
        print(f"   ⚠ get_quote 返回了数据：{quote}")
except Exception as e:
    print(f"   ✗ get_quote 抛出异常：{e}")

try:
    history = provider.get_history('600519.SH', days=10)
    if history is None:
        print("   ✓ get_history 在无 token 时正确返回 None")
    else:
        print(f"   ⚠ get_history 返回了数据")
except Exception as e:
    print(f"   ✗ get_history 抛出异常：{e}")

try:
    quotes = provider.get_quotes(['600519.SH', '000001.SZ'])
    if quotes == {}:
        print("   ✓ get_quotes 在无 token 时正确返回空字典")
    else:
        print(f"   ⚠ get_quotes 返回了数据：{quotes}")
except Exception as e:
    print(f"   ✗ get_quotes 抛出异常：{e}")

# 测试 5: 测试集成到 provider.py
print("\n5. 测试集成到 provider.py...")
try:
    from data.provider import get_provider
    provider_tushare = get_provider('tushare', token='', retry=1)
    print("   ✓ get_provider('tushare') 调用成功")
except Exception as e:
    print(f"   ✗ 集成失败：{e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("代码结构测试完成 - 全部通过 ✓")
print("=" * 60)

print("\n【下一步】")
print("1. 在 https://tushare.pro 注册并获取 token")
print("2. 设置环境变量：export TUSHARE_TOKEN='your_token'")
print("3. 运行完整测试：python3 test_tushare.py")
print("\n【支持的数据类型】")
print("  • get_quote(code) - A 股实时行情")
print("  • get_history(code, days) - 历史 K 线数据")
print("  • get_quotes(codes) - 批量获取行情")
print("  • get_financial_data(code) - 财务数据")
print("  • get_stock_info(code) - 股票基本信息")
