# -*- coding: utf-8 -*-
"""
Infoway API 详细测试脚本
根据官方限制信息配置测试
"""

import requests
import time
import json
from datetime import datetime

# 配置
TOKEN = 'c87ebee1fe204f40acc35ed0272677d3-infoway'

# 可能的 API 基础地址
POSSIBLE_BASE_URLS = [
    'https://api.infoway.io',
    'https://api.iinfoway.com',
    'https://open.infoway.io',
    'https://data.infoway.io',
    'https://quote.infoway.io',
]

# 可能的 API 端点
POSSIBLE_ENDPOINTS = [
    '/quote',
    '/v1/quote',
    '/v2/quote',
    '/stock/quote',
    '/market/quote',
    '/realtime',
    '/realtime/quote',
    '/hq',
    '/market',
]

# 测试股票（A 股格式）
TEST_STOCKS = [
    '601398.SH',  # 工商银行
    '600036.SH',  # 招商银行
    '600519.SH',  # 贵州茅台
    '000858.SZ',  # 五粮液
    '000333.SZ',  # 美的集团
]

def test_api_endpoints():
    """测试所有可能的 API 端点组合"""
    
    print("="*70)
    print("🧪 Infoway API 全面测试")
    print("="*70)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Token: {TOKEN[:30]}...")
    print(f"限制：60 次/分钟，86400 次/日")
    print("="*70)
    
    results = []
    
    # 测试不同的基础 URL + 端点组合
    for base_url in POSSIBLE_BASE_URLS:
        for endpoint in POSSIBLE_ENDPOINTS:
            url = f"{base_url}{endpoint}"
            
            # 尝试不同的参数格式
            for stock in TEST_STOCKS[:2]:
                # 格式 1: ?token=xxx&symbol=xxx
                params1 = {'token': TOKEN, 'symbol': stock}
                
                # 格式 2: ?api_key=xxx&code=xxx
                params2 = {'api_key': TOKEN, 'code': stock}
                
                # 格式 3: Header 认证
                headers = {'Authorization': f'Bearer {TOKEN}'}
                params3 = {'symbol': stock}
                
                for params, headers_used, format_name in [
                    (params1, {}, 'URL 参数 1'),
                    (params2, {}, 'URL 参数 2'),
                    (params3, headers, 'Header 认证'),
                ]:
                    try:
                        print(f"\n测试：{url}")
                        print(f"  格式：{format_name}")
                        print(f"  股票：{stock}")
                        
                        response = requests.get(
                            url, 
                            params=params, 
                            headers=headers_used,
                            timeout=5
                        )
                        
                        result = {
                            'url': url,
                            'format': format_name,
                            'stock': stock,
                            'status': response.status_code,
                            'success': response.status_code == 200
                        }
                        results.append(result)
                        
                        if response.status_code == 200:
                            print(f"  ✅ 成功！HTTP 200")
                            try:
                                data = response.json()
                                print(f"  响应数据：{json.dumps(data, ensure_ascii=False)[:300]}")
                                return True, url, data
                            except:
                                print(f"  响应：{response.text[:300]}")
                            return True, url, response.text
                        else:
                            print(f"  ❌ HTTP {response.status_code}")
                            if response.status_code == 401:
                                print(f"     认证失败 - Token 可能无效")
                            elif response.status_code == 404:
                                print(f"     端点不存在")
                            elif response.status_code == 429:
                                print(f"     请求超限")
                    
                    except Exception as e:
                        print(f"  ❌ 异常：{str(e)[:100]}")
                        continue
    
    return False, None, None

def main():
    success, url, data = test_api_endpoints()
    
    print("\n" + "="*70)
    print("📊 测试结果汇总")
    print("="*70)
    
    if success:
        print(f"✅ 找到可用的 API 端点！")
        print(f"URL: {url}")
        print(f"\n建议配置:")
        print(f"""
INFOWAY_CONFIG = {{
    'token': '{TOKEN}',
    'api_url': '{url}',
    'batch_size': 10,
    'interval_seconds': 15,
    'enabled': True,
}}
        """)
    else:
        print("❌ 未找到可用的 API 端点")
        print("\n建议:")
        print("1. 查看 Infoway 官方文档确认 API 地址")
        print("2. 检查 Token 是否有效")
        print("3. 联系 Infoway 技术支持")
        print("4. 继续使用腾讯财经（已验证稳定）")
    
    print("="*70)

if __name__ == '__main__':
    main()
