#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yfinance 数据源测试脚本

使用方法:
    python3 test_yfinance.py

注意：yfinance 有速率限制，建议首次运行失败后等待 1-2 分钟再试
"""
import sys
import time
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies/bobquant')

from data.yfinance_provider import YFinanceProvider


def test_basic():
    """基础测试"""
    print("=" * 70)
    print("BobQuant yfinance 数据源测试")
    print("=" * 70)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 创建数据源实例 (delay=3 秒避免速率限制)
    provider = YFinanceProvider(retry=3, timeout=30, delay=3.0)
    
    # 测试股票列表
    test_stocks = [
        ('AAPL', '美股 - 苹果公司'),
        ('MSFT', '美股 - 微软'),
        ('GOOGL', '美股 - 谷歌'),
        ('hk00700', '港股 - 腾讯控股'),
        ('sh600519', 'A 股 - 贵州茅台'),
    ]
    
    results = {'success': 0, 'failed': 0}
    
    # 测试 1: 实时行情
    print("【测试 1】实时行情获取 (get_quote)")
    print("-" * 70)
    for code, desc in test_stocks:
        print(f"\n[{code}] {desc}...", end=' ', flush=True)
        quote = provider.get_quote(code)
        
        if quote:
            results['success'] += 1
            print("✓")
            print(f"       名称：{quote['name']}")
            print(f"       现价：{quote['current']:.2f}")
            print(f"       涨跌：{quote['change']:+.2f}%")
            print(f"       成交量：{quote['volume']:,.0f}")
        else:
            results['failed'] += 1
            print("✗ (可能遇到速率限制)")
        
        # 额外延迟避免速率限制
        time.sleep(1)
    
    # 测试 2: 历史数据
    print("\n\n【测试 2】历史数据获取 (get_history)")
    print("-" * 70)
    for code, desc in [('AAPL', '苹果'), ('MSFT', '微软')]:
        print(f"\n[{code}] 获取 10 天历史数据...", end=' ', flush=True)
        df = provider.get_history(code, days=10)
        
        if df is not None and not df.empty:
            print("✓")
            print(f"       记录数：{len(df)} 条")
            print(f"       日期：{df.index[0].strftime('%Y-%m-%d')} 至 {df.index[-1].strftime('%Y-%m-%d')}")
            print(f"       最新收盘：{df['close'].iloc[-1]:.2f}")
        else:
            print("✗")
        
        time.sleep(2)
    
    # 测试 3: 批量获取
    print("\n\n【测试 3】批量获取 (get_quotes)")
    print("-" * 70)
    codes = ['AAPL', 'MSFT', 'GOOGL']
    print(f"批量获取：{', '.join(codes)}")
    quotes = provider.get_quotes(codes)
    
    for code in codes:
        if code in quotes:
            q = quotes[code]
            print(f"  ✓ {code}: {q['current']:.2f} ({q['change']:+.2f}%)")
        else:
            print(f"  ✗ {code}: 获取失败")
    
    # 测试结果
    print("\n" + "=" * 70)
    print(f"测试结果：成功 {results['success']}/{len(test_stocks)} 只股票")
    print("=" * 70)
    
    if results['success'] == 0:
        print("\n⚠️  所有请求都失败了，可能遇到 yfinance 速率限制")
        print("   建议：")
        print("   1. 等待 1-2 分钟后重试")
        print("   2. 增加 delay 参数 (建议 3-5 秒)")
        print("   3. 减少重试次数")
        print("   4. 生产环境考虑使用付费 API")
    
    return results['success'] > 0


def test_integration():
    """集成测试 - 通过 provider.py 获取"""
    print("\n\n" + "=" * 70)
    print("集成测试：通过 provider.py 获取 yfinance 数据源")
    print("=" * 70)
    
    try:
        from data.provider import get_provider
        
        print("\n获取 yfinance 数据源实例...")
        provider = get_provider('yfinance', retry=2, delay=3.0)
        print(f"✓ 成功创建：{type(provider).__name__}")
        
        print("\n测试获取 AAPL 行情...")
        quote = provider.get_quote('AAPL')
        if quote:
            print(f"✓ 成功：{quote['name']} - ${quote['current']:.2f}")
            return True
        else:
            print("✗ 失败")
            return False
            
    except Exception as e:
        print(f"✗ 集成测试失败：{e}")
        return False


if __name__ == '__main__':
    print("\n⚠️  注意：yfinance 有速率限制，首次运行可能失败")
    print("   如失败请等待 1-2 分钟后重试\n")
    
    success1 = test_basic()
    success2 = test_integration()
    
    print("\n" + "=" * 70)
    if success1 or success2:
        print("✓ 测试通过")
    else:
        print("⚠️  测试未通过 (可能是速率限制，稍后重试)")
    print("=" * 70 + "\n")
