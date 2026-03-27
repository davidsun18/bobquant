"""
P2因子测试脚本
验证P0+P1+P2完整因子链
"""

import sys
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

from bobquant_v2.api import MarketAPI
from bobquant_v2.indicator.technical import all_indicators
from bobquant_v2.indicator.advanced import AdvancedFactors
from bobquant_v2.strategy.p2_strategy import create_p2_strategy


def test_p2_factors():
    """测试P2高级因子"""
    print("=" * 70)
    print("测试 P0+P1+P2 完整因子链")
    print("=" * 70)
    
    # 获取历史数据
    market_api = MarketAPI()
    
    test_codes = ['sh.600519']  # 以茅台为例
    
    for code in test_codes:
        print(f"\n📊 测试 {code}:")
        
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
            
            # 计算所有指标 (P0+P1+P2)
            df = all_indicators(df, include_p2=True)
            
            # 生成P2信号
            p2_signals = AdvancedFactors.generate_p2_signals(df)
            
            # 获取最新数据
            latest = df.iloc[-1]
            
            print(f"  ✅ 数据正常 ({len(df)}天)")
            
            # P0指标
            print(f"\n  📈 P0 - 核心指标:")
            print(f"     MACD: {latest.get('macd_line', 0):.2f}")
            print(f"     RSI: {latest.get('rsi', 0):.1f}")
            print(f"     MA20: {latest.get('ma20', 0):.2f}")
            
            # P1指标
            print(f"\n  📊 P1 - 增强指标:")
            print(f"     KDJ: K={latest.get('kdj_k', 0):.1f}, D={latest.get('kdj_d', 0):.1f}")
            print(f"     布林带: {latest.get('boll_pct', 0)*100:.1f}%")
            print(f"     ATR: {latest.get('atr', 0):.2f}")
            
            # P2指标
            print(f"\n  🎯 P2 - 高级指标:")
            print(f"     趋势强度: {p2_signals.get('trend_strength', 0):.0f} ({p2_signals.get('trend_quality')})")
            print(f"     波动率: {p2_signals.get('volatility', 0):.1f}% ({p2_signals.get('vol_state')})")
            print(f"     MFI: {p2_signals.get('mfi', 0):.0f}")
            print(f"     形态得分: {p2_signals.get('pattern_score', 0):.0f}")
            print(f"     多周期一致性: {p2_signals.get('timeframe_consistency', 0):.2f}")
            
            # 技术形态
            print(f"\n  🔍 技术形态:")
            print(f"     锤子线: {'✅' if p2_signals.get('has_hammer') else '❌'}")
            print(f"     吞没形态: {'✅' if p2_signals.get('has_engulfing') else '❌'}")
            print(f"     星线形态: {'✅' if p2_signals.get('has_star') else '❌'}")
            print(f"     多头排列: {'✅' if p2_signals.get('bullish_alignment') else '❌'}")
            
            # P2综合评分
            print(f"\n  💯 P2调整后评分: {p2_signals.get('p2_adjusted_score', 50):.0f}")
            
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)


def test_p2_strategy():
    """测试P2策略引擎"""
    print("\n" + "=" * 70)
    print("测试 P2 策略引擎")
    print("=" * 70)
    
    # 创建P2策略
    strategy = create_p2_strategy('balanced')
    
    print("\n✅ P2策略创建成功")
    print(f"  最小趋势强度: {strategy.p2_config['min_trend_score']}")
    print(f"  最大波动率: {strategy.p2_config['max_volatility']}%")
    print(f"  要求资金流入: {strategy.p2_config['require_money_inflow']}")
    
    # 测试不同风格
    for style in ['conservative', 'balanced', 'aggressive']:
        s = create_p2_strategy(style)
        print(f"\n  📌 {style}策略:")
        print(f"     趋势要求: {s.p2_config['min_trend_score']}")
        print(f"     风险承受: {s.p2_config['max_volatility']}%")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    print("\n🚀 BobQuant V2 P2因子测试\n")
    
    test_p2_factors()
    test_p2_strategy()
    
    print("\n✅ P2测试完成！")
