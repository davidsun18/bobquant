"""
因子测试脚本
验证P0+P1因子是否正常工作
"""

import sys
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

from bobquant_v2.api import MarketAPI
from bobquant_v2.indicator.technical import all_indicators, generate_signals
from bobquant_v2.strategy.factor_strategy import create_strategy


def test_indicators():
    """测试技术指标"""
    print("=" * 60)
    print("测试 P0+P1 技术指标因子")
    print("=" * 60)
    
    # 获取历史数据
    market_api = MarketAPI()
    
    # 测试股票
    test_codes = ['sh.600519', 'sz.300750', 'sh.601398']
    
    for code in test_codes:
        print(f"\n📊 测试 {code}:")
        
        # 获取历史数据（使用baostock）
        try:
            import baostock as bs
            lg = bs.login()
            
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
            
            rs = bs.query_history_k_data_plus(
                code, "date,open,high,low,close,volume",
                start_date=start_date, end_date=end_date, frequency="d"
            )
            
            data_list = []
            while (rs.error_code == '0') and rs.next():
                data_list.append(rs.get_row_data())
            
            bs.logout()
            
            if len(data_list) < 30:
                print(f"  ⚠️ 数据不足 ({len(data_list)}天)")
                continue
            
            import pandas as pd
            df = pd.DataFrame(data_list, columns=rs.fields)
            df = df.astype({
                'open': float, 'high': float, 'low': float,
                'close': float, 'volume': float
            })
            df['date'] = pd.to_datetime(df['date'])
            
            # 计算所有指标
            df = all_indicators(df)
            
            # 生成信号
            signals = generate_signals(df)
            
            # 获取最新数据
            latest = df.iloc[-1]
            
            print(f"  ✅ 数据正常 ({len(df)}天)")
            print(f"  📈 MACD: {'金叉' if latest.get('macd_golden') else '死叉' if latest.get('macd_death') else '中性'}")
            print(f"  📊 RSI: {latest.get('rsi', 0):.1f}")
            print(f"  📉 KDJ: K={latest.get('kdj_k', 0):.1f}, D={latest.get('kdj_d', 0):.1f}, J={latest.get('kdj_j', 0):.1f}")
            print(f"  🎯 布林带: {latest.get('boll_pct', 0)*100:.1f}%")
            print(f"  💯 综合评分: {signals.get('composite_score', 50)}")
            print(f"  📋 信号: MACD={signals.get('macd_signal')}, RSI={signals.get('rsi_signal')}, KDJ={signals.get('kdj_signal')}")
            
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
    
    print("\n" + "=" * 60)


def test_strategy():
    """测试策略引擎"""
    print("\n" + "=" * 60)
    print("测试策略引擎")
    print("=" * 60)
    
    # 创建策略
    strategy = create_strategy('balanced')
    
    print("\n✅ 策略创建成功")
    print(f"  配置: RSI买入阈值={strategy.rsi_buy_threshold}")
    print(f"  配置: 评分买入阈值={strategy.score_buy_threshold}")
    
    # 测试不同风格的策略
    for style in ['conservative', 'balanced', 'aggressive']:
        s = create_strategy(style)
        print(f"\n  📌 {style}策略:")
        print(f"     RSI区间: {s.rsi_buy_threshold}-{s.rsi_sell_threshold}")
        print(f"     评分区间: {s.score_sell_threshold}-{s.score_buy_threshold}")
    
    print("\n" + "=" * 60)


def test_realtime():
    """测试实时行情"""
    print("\n" + "=" * 60)
    print("测试实时行情获取")
    print("=" * 60)
    
    market_api = MarketAPI()
    
    # 测试单只股票
    print("\n📊 单只股票行情:")
    quote = market_api.get('sh.600519')
    if quote:
        print(f"  ✅ 贵州茅台: ¥{quote['current']:.2f} ({quote['change']:+.2f}%)")
    else:
        print("  ❌ 获取失败")
    
    # 测试批量获取
    print("\n📊 批量行情获取:")
    codes = ['sh.600519', 'sz.300750', 'sh.601398', 'sh.601318']
    quotes = market_api.get_batch(codes)
    for code, quote in quotes.items():
        print(f"  ✅ {quote['name']}: ¥{quote['current']:.2f}")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    print("\n🚀 BobQuant V2 因子测试\n")
    
    # 运行测试
    test_indicators()
    test_strategy()
    test_realtime()
    
    print("\n✅ 所有测试完成！")
