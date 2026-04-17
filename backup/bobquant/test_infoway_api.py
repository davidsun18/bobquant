# -*- coding: utf-8 -*-
"""
Infoway API 测试脚本
测试实时数据获取
"""

import requests
import time
import json
from datetime import datetime

# 配置
TOKEN = 'c87ebee1fe204f40acc35ed0272677d3-infoway'
BASE_URL = 'https://api.infoway.io'

# 测试股票池（10 只）
TEST_STOCKS = [
    'sh.601398', 'sh.600036', 'sh.600519',
    'sz.000858', 'sz.000333', 'sh.600887',
    'sh.600276', 'sz.002594', 'sz.300750',
    'sh.600547',
]

def test_infoway_api():
    """测试 Infoway API 各种接口"""
    
    print("="*70)
    print("🧪 Infoway API 测试")
    print("="*70)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Token: {TOKEN[:20]}...")
    print("="*70)
    
    # 测试 1: 单只股票查询
    print("\n📊 测试 1: 单只股票查询")
    print("-"*70)
    
    for code in TEST_STOCKS[:3]:
        symbol = code.replace('.', '')
        
        # 尝试不同的 API 端点
        endpoints_to_try = [
            f'{BASE_URL}/quote?token={TOKEN}&symbol={symbol}',
            f'{BASE_URL}/v1/quote?token={TOKEN}&symbol={symbol}',
            f'{BASE_URL}/stock/quote?token={TOKEN}&code={symbol}',
            f'{BASE_URL}/market/quote?token={TOKEN}&symbol={symbol}',
        ]
        
        for endpoint in endpoints_to_try:
            try:
                print(f"  测试：{endpoint[:60]}...")
                response = requests.get(endpoint, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✅ 成功！HTTP 200")
                    print(f"  响应：{json.dumps(data, indent=2)[:500]}")
                    return True, data
                else:
                    print(f"  ❌ HTTP {response.status_code}")
            
            except Exception as e:
                print(f"  ❌ 异常：{str(e)[:100]}")
                continue
        
        print()
    
    # 测试 2: 批量查询
    print("\n📊 测试 2: 批量查询")
    print("-"*70)
    
    codes = ','.join([s.replace('.', '') for s in TEST_STOCKS[:5]])
    
    batch_endpoints = [
        f'{BASE_URL}/batch?token={TOKEN}&codes={codes}',
        f'{BASE_URL}/v1/batch?token={TOKEN}&codes={codes}',
        f'{BASE_URL}/quotes?token={TOKEN}&symbols={codes}',
    ]
    
    for endpoint in batch_endpoints:
        try:
            print(f"  测试：{endpoint[:60]}...")
            response = requests.get(endpoint, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ 成功！HTTP 200")
                print(f"  响应：{json.dumps(data, indent=2)[:500]}")
                return True, data
            else:
                print(f"  ❌ HTTP {response.status_code}")
        
        except Exception as e:
            print(f"  ❌ 异常：{str(e)[:100]}")
            continue
    
    return False, None

def main():
    success, data = test_infoway_api()
    
    print("\n" + "="*70)
    print("📊 测试结果")
    print("="*70)
    
    if success:
        print("✅ Infoway API 可用！")
        print("建议配置到系统中使用")
    else:
        print("❌ Infoway API 测试失败")
        print("可能原因:")
        print("  1. API 地址不正确")
        print("  2. Token 无效或过期")
        print("  3. 网络问题/DNS 解析失败")
        print("  4. 需要查看官方文档确认 API 格式")
    
    print("="*70)

if __name__ == '__main__':
    main()
