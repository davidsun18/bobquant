# -*- coding: utf-8 -*-
"""
iTick 批量查询测试脚本
测试 10 只/次的批量查询性能
"""

import requests
import time
import json

# 配置
TOKEN = '65d8251c19b64a68a39c56aa0aa39071e1632ac0f8624b8fb053f61b10303b0a'
API_URL = 'https://api.itick.com/quote'
BATCH_SIZE = 10  # 每次 10 只

# 测试股票池（50 只）
TEST_STOCKS = [
    'sh.601398', 'sh.601288', 'sh.601939', 'sh.600036', 'sh.601166',
    'sh.600016', 'sh.601988', 'sh.601328', 'sh.601658', 'sz.000001',
    'sh.600519', 'sh.000858', 'sz.000568', 'sh.600809', 'sh.600702',
    'sh.600779', 'sh.603198', 'sh.603369', 'sh.601138', 'sh.688981',
    'sz.002371', 'sz.002156', 'sz.002185', 'sz.002049', 'sz.002415',
    'sh.600584', 'sh.603501', 'sh.603986', 'sz.002594', 'sz.300750',
    'sz.002460', 'sz.002466', 'sz.002709', 'sz.002812', 'sh.601012',
    'sh.600438', 'sh.600276', 'sh.600085', 'sh.600436', 'sh.603259',
    'sz.000538', 'sz.000661', 'sz.000333', 'sz.000651', 'sh.600887',
    'sh.600690', 'sh.601888', 'sh.600028', 'sh.600309', 'sh.600547',
]

def test_batch_query(codes):
    """测试批量查询"""
    params = {'token': TOKEN, 'codes': ','.join(codes)}
    headers = {'User-Agent': 'OpenClaw-Quant/1.0', 'Accept': 'application/json'}
    
    start_time = time.time()
    elapsed = 0
    
    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=10)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'ok':
                count = len(data.get('data', []))
                return {
                    'success': True,
                    'count': count,
                    'elapsed_ms': elapsed * 1000,
                    'data': data.get('data', [])
                }
            else:
                return {
                    'success': False,
                    'error': f'API 返回错误：{data}',
                    'elapsed_ms': elapsed * 1000
                }
        else:
            return {
                'success': False,
                'error': f'HTTP {response.status_code}: {response.text}',
                'elapsed_ms': elapsed * 1000
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'异常：{str(e)}',
            'elapsed_ms': elapsed * 1000
        }

def main():
    print("="*70)
    print("🧪 iTick 批量查询测试")
    print("="*70)
    print(f"批量大小：{BATCH_SIZE} 只/次")
    print(f"股票池：{len(TEST_STOCKS)} 只")
    print(f"预计查询次数：{len(TEST_STOCKS) // BATCH_SIZE} 次")
    print("="*70)
    
    results = []
    total_success = 0
    total_failed = 0
    total_stocks = 0
    total_time = 0
    
    # 分批测试
    for i in range(0, len(TEST_STOCKS), BATCH_SIZE):
        batch = TEST_STOCKS[i:i+BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        
        print(f"\n📊 批次 {batch_num}: 查询 {len(batch)} 只股票...")
        print(f"   股票：{', '.join(batch)}")
        
        result = test_batch_query(batch)
        results.append(result)
        
        if result['success']:
            total_success += 1
            total_stocks += result['count']
            print(f"   ✅ 成功：获取到 {result['count']} 只股票数据")
            print(f"   ⏱️  耗时：{result['elapsed_ms']:.0f}ms")
            
            # 显示前 3 只股票详情
            for stock in result['data'][:3]:
                name = stock.get('name', 'N/A')
                price = stock.get('price', 0)
                change = stock.get('change', 0)
                print(f"     - {name}: ¥{price} ({change:+.2f}%)")
        else:
            total_failed += 1
            print(f"   ❌ 失败：{result['error']}")
        
        total_time += result['elapsed_ms']
        
        # 避免触发限流，等待 1 秒
        time.sleep(1)
    
    # 汇总统计
    print("\n" + "="*70)
    print("📊 测试结果汇总")
    print("="*70)
    
    total_queries = total_success + total_failed
    success_rate = (total_success / total_queries * 100) if total_queries > 0 else 0
    avg_time = total_time / total_queries if total_queries > 0 else 0
    
    print(f"总查询次数：{total_queries} 次")
    print(f"成功次数：{total_success} 次")
    print(f"失败次数：{total_failed} 次")
    print(f"成功率：{success_rate:.1f}%")
    print(f"平均响应时间：{avg_time:.0f}ms")
    print(f"获取股票数据：{total_stocks} 只次")
    print(f"总耗时：{total_time/1000:.1f}秒")
    
    # 性能评估
    print("\n" + "="*70)
    print("📈 性能评估")
    print("="*70)
    
    if success_rate >= 95 and avg_time < 500:
        print("✅ 优秀！适合生产使用")
    elif success_rate >= 85 and avg_time < 1000:
        print("✅ 良好，可以正常使用")
    elif success_rate >= 70:
        print("⚠️ 一般，建议优化")
    else:
        print("❌ 较差，需要检查")
    
    # 与腾讯财经对比
    print("\n" + "="*70)
    print("📊 对比腾讯财经（单只查询 ~100ms）")
    print("="*70)
    
    tencent_time = len(TEST_STOCKS) * 100  # 假设每只 100ms
    itick_time = total_time
    
    print(f"腾讯财经（单只轮询）: {tencent_time}ms")
    print(f"iTick（批量 10 只）: {itick_time:.0f}ms")
    print(f"速度提升：{tencent_time/itick_time:.1f}x" if itick_time > 0 else "N/A")
    
    # 保存结果
    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'batch_size': BATCH_SIZE,
        'total_stocks': len(TEST_STOCKS),
        'total_queries': total_queries,
        'success': total_success,
        'failed': total_failed,
        'success_rate': success_rate,
        'avg_response_ms': avg_time,
        'total_time_ms': total_time
    }
    
    with open('/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/iTick 测试报告.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 测试报告已保存：sim_trading/iTick 测试报告.json")
    print("="*70)

if __name__ == '__main__':
    main()
