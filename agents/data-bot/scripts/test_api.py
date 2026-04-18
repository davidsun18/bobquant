#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Bot - API 连接测试脚本
测试腾讯财经和 BaoStock API 连接
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from collect_data import TencentDataCollector, BaoStockCollector, load_stock_list

def test_tencent_api():
    """测试腾讯财经 API"""
    print("\n" + "=" * 60)
    print("测试腾讯财经 API")
    print("=" * 60)
    
    collector = TencentDataCollector()
    
    # 测试单只股票
    test_stocks = ['600519', '000001', '000858']
    
    for stock in test_stocks:
        print(f"\n测试股票：{stock}")
        quote = collector.get_realtime_quote(stock)
        
        if quote:
            print(f"  ✓ 获取成功")
            print(f"    股票名称：{quote['stock_name']}")
            print(f"    当前价格：{quote['current_price']}")
            print(f"    涨跌幅：{quote['change_pct']}%")
            print(f"    成交量：{quote['volume']} 手")
            print(f"    成交额：{quote['turnover']} 元")
        else:
            print(f"  ✗ 获取失败")
    
    # 测试批量获取
    print("\n" + "-" * 60)
    print("测试批量获取 (前 10 只股票)")
    print("-" * 60)
    
    stock_list = load_stock_list()[:10]
    df = collector.get_batch_quotes(stock_list)
    
    if not df.empty:
        print(f"✓ 批量获取成功：{len(df)} 只股票")
        print(f"\n数据预览:")
        print(df[['stock_code', 'stock_name', 'current_price', 'change_pct']].to_string())
    else:
        print("✗ 批量获取失败")
    
    return not df.empty


def test_baostock_api():
    """测试 BaoStock API"""
    print("\n" + "=" * 60)
    print("测试 BaoStock API")
    print("=" * 60)
    
    collector = BaoStockCollector()
    
    # 测试登录
    print("\n测试登录...")
    collector.login()
    
    if collector.login_done:
        print("✓ 登录成功")
    else:
        print("✗ 登录失败")
        return False
    
    # 测试获取历史数据
    print("\n测试获取历史数据 (贵州茅台，最近 5 天)")
    df = collector.get_history_data('600519', '2026-04-10', '2026-04-18')
    
    if df is not None and not df.empty:
        print(f"✓ 获取成功：{len(df)} 条记录")
        print(f"\n数据预览:")
        print(df[['date', 'open', 'high', 'low', 'close', 'volume']].to_string())
    else:
        print("✗ 获取失败或无数据")
    
    # 测试获取股票列表
    print("\n" + "-" * 60)
    print("测试获取 A 股股票列表")
    print("-" * 60)
    
    list_df = collector.get_stock_list()
    
    if list_df is not None and not list_df.empty:
        print(f"✓ 获取成功：{len(list_df)} 只股票")
        # 统计沪深股票数量
        if 'code' in list_df.columns:
            sh_count = list_df['code'].str.startswith('sh', na=False).sum()
            sz_count = list_df['code'].str.startswith('sz', na=False).sum()
            print(f"    上海：{sh_count} 只")
            print(f"    深圳：{sz_count} 只")
    else:
        print("✗ 获取失败")
    
    collector.logout()
    
    return True


def main():
    print("\n" + "🚀" * 30)
    print("Data Bot - API 连接测试")
    print("🚀" * 30)
    
    results = {
        'tencent': False,
        'baostock': False
    }
    
    try:
        results['tencent'] = test_tencent_api()
    except Exception as e:
        print(f"\n✗ 腾讯财经测试异常：{e}")
    
    try:
        results['baostock'] = test_baostock_api()
    except Exception as e:
        print(f"\n✗ BaoStock 测试异常：{e}")
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    print(f"腾讯财经：{'✓ 通过' if results['tencent'] else '✗ 失败'}")
    print(f"BaoStock:  {'✓ 通过' if results['baostock'] else '✗ 失败'}")
    
    if results['tencent'] and results['baostock']:
        print("\n🎉 所有测试通过！数据采集脚本可以正常使用。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查网络连接或 API 配置。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
