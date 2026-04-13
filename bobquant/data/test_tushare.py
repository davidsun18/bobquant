# -*- coding: utf-8 -*-
"""
Tushare 数据源测试脚本

测试前请确保：
1. 已安装 tushare: pip3 install tushare
2. 已设置 TUSHARE_TOKEN 环境变量或在代码中传入 token

使用方法:
    python3 test_tushare.py
"""
import sys
import os
import time

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.tushare_provider import TushareProvider


def test_tushare_provider():
    """测试 Tushare 数据源"""
    print("=" * 60)
    print("Tushare 数据源测试")
    print("=" * 60)
    
    # 从环境变量获取 token
    token = os.environ.get('TUSHARE_TOKEN', '')
    if not token:
        print("\n[警告] 未设置 TUSHARE_TOKEN 环境变量")
        print("请在 https://tushare.pro 注册并获取 token")
        print("然后设置环境变量：export TUSHARE_TOKEN='your_token'")
        print("\n继续测试可能无法获取数据...\n")
    
    provider = TushareProvider(token=token, retry=2, delay=1.0)
    
    # 测试股票列表 (A 股，Tushare 格式)
    test_stocks = [
        ('600519.SH', '贵州茅台'),
        ('000001.SZ', '平安银行'),
        ('601318.SH', '中国平安'),
        ('000002.SZ', '万科 A'),
        ('600036.SH', '招商银行'),
    ]
    
    success_count = 0
    
    print("\n1. 测试实时行情获取 (get_quote)")
    print("-" * 60)
    for code, name in test_stocks:
        print(f"\n获取 {name} ({code})...", end=" ")
        quote = provider.get_quote(code)
        if quote:
            print(f"✓")
            print(f"  名称：{quote['name']}")
            print(f"  当前价：{quote['current']:.2f}")
            print(f"  涨跌幅：{quote['change']:+.2f}%")
            success_count += 1
        else:
            print(f"✗ 获取失败")
        time.sleep(0.5)
    
    print("\n\n2. 测试历史数据获取 (get_history)")
    print("-" * 60)
    history_success = 0
    for code, name in test_stocks[:3]:
        print(f"\n获取 {name} ({code}) 历史数据 (10 天)...")
        df = provider.get_history(code, days=10)
        if df is not None and not df.empty:
            print(f"  ✓ 获取成功，共 {len(df)} 条记录")
            print(f"  ✓ 最新收盘价：{df['close'].iloc[-1]:.2f}")
            history_success += 1
        else:
            print(f"  ✗ 获取失败")
        time.sleep(0.5)
    
    print("\n\n3. 测试批量获取 (get_quotes)")
    print("-" * 60)
    codes = [code for code, _ in test_stocks]
    print(f"批量获取 {len(codes)} 只股票...")
    quotes = provider.get_quotes(codes)
    batch_success = 0
    for code, quote in quotes.items():
        if quote:
            print(f"  ✓ {code}: {quote['current']:.2f} ({quote['change']:+.2f}%)")
            batch_success += 1
        else:
            print(f"  ✗ {code}: 获取失败")
    
    print("\n\n4. 测试股票基本信息 (get_stock_info)")
    print("-" * 60)
    info_success = 0
    for code, name in test_stocks[:2]:
        print(f"\n获取 {name} ({code}) 基本信息...")
        info = provider.get_stock_info(code)
        if info:
            print(f"  ✓ 名称：{info['name']}")
            print(f"  ✓ 地区：{info['area']}")
            print(f"  ✓ 行业：{info['industry']}")
            info_success += 1
        else:
            print(f"  ✗ 获取失败")
        time.sleep(0.5)
    
    print("\n\n5. 测试财务数据 (get_financial_data)")
    print("-" * 60)
    financial_success = 0
    for code, name in test_stocks[:2]:
        print(f"\n获取 {name} ({code}) 财务数据...")
        financial = provider.get_financial_data(code)
        if financial:
            print(f"  ✓ 市盈率 (PE): {financial['pe']}")
            print(f"  ✓ 市净率 (PB): {financial['pb']}")
            print(f"  ✓ 净资产收益率 (ROE): {financial['roe']}")
            financial_success += 1
        else:
            print(f"  ✗ 获取失败")
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    # 输出总结
    print(f"\n【测试结果】")
    print(f"  实时行情 (单只): {success_count}/{len(test_stocks)} 成功")
    print(f"  历史数据：{history_success}/3 成功")
    print(f"  批量获取：{batch_success}/{len(codes)} 成功")
    print(f"  股票信息：{info_success}/2 成功")
    print(f"  财务数据：{financial_success}/2 成功")
    
    # 总体评价
    total = success_count + history_success + batch_success + info_success + financial_success
    max_total = len(test_stocks) + 3 + len(codes) + 2 + 2
    success_rate = total / max_total * 100 if max_total > 0 else 0
    
    print(f"\n  总体成功率：{success_rate:.1f}% ({total}/{max_total})")
    
    if success_rate >= 80:
        print(f"\n✓ Tushare 数据源工作正常!")
    elif success_rate >= 50:
        print(f"\n⚠ Tushare 数据源基本可用，建议检查 token 和网络")
    else:
        print(f"\n✗ Tushare 数据源可能存在问题，请检查:")
        print(f"  1. Tushare token 是否正确设置")
        print(f"  2. 网络连接是否正常")
        print(f"  3. Tushare 积分是否足够 (部分接口需要积分)")
    
    return success_rate


if __name__ == '__main__':
    test_tushare_provider()
