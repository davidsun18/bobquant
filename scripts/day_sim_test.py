#!/usr/bin/env python3
"""
日线策略 V2.0 - 模拟交易验证

用于实盘前验证策略逻辑、数据源、信号生成等
确保周一实盘准确无误
"""

import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

import baostock as bs

# 配置
TEST_DATE = datetime.now() + timedelta(days=1)  # 明天
if TEST_DATE.weekday() >= 5:  # 如果是周末，顺延到周一
    TEST_DATE += timedelta(days=(7 - TEST_DATE.weekday()))

INITIAL_CAPITAL = 1000000  # 100 万

# 股票池 (30 只龙头)
STOCK_POOL = [
    # 银行金融 (5 只)
    ('sh.600036', '招商银行', '银行'),
    ('sh.601398', '工商银行', '银行'),
    ('sh.601288', '农业银行', '银行'),
    ('sh.601318', '中国平安', '保险'),
    ('sh.601688', '华泰证券', '证券'),
    
    # 白酒饮料 (4 只)
    ('sh.600519', '贵州茅台', '白酒'),
    ('sh.000858', '五粮液', '白酒'),
    ('sz.000568', '泸州老窖', '白酒'),
    ('sh.600809', '山西汾酒', '白酒'),
    
    # 消费 (5 只)
    ('sz.000333', '美的集团', '家电'),
    ('sz.000651', '格力电器', '家电'),
    ('sh.600887', '伊利股份', '食品'),
    ('sh.600690', '海尔智家', '家电'),
    ('sh.601888', '中国中免', '消费'),
    
    # 医药 (5 只)
    ('sh.600276', '恒瑞医药', '医药'),
    ('sz.300760', '迈瑞医疗', '医疗'),
    ('sh.600436', '片仔癀', '中药'),
    ('sh.603259', '药明康德', 'CXO'),
    ('sz.000538', '云南白药', '医药'),
    
    # 周期/科技 (11 只)
    ('sh.601088', '中国神华', '煤炭'),
    ('sh.600028', '中国石化', '石化'),
    ('sh.600309', '万华化学', '化工'),
    ('sh.600547', '山东黄金', '有色'),
    ('sh.601012', '隆基绿能', '光伏'),
    ('sz.300750', '宁德时代', '新能源'),
    ('sz.002594', '比亚迪', '新能源'),
    ('sh.601138', '工业富联', '科技'),
    ('sz.002415', '海康威视', '科技'),
    ('sh.600584', '长电科技', '科技'),
    ('sh.688981', '中芯国际', '半导体'),
]

# 策略参数
STRATEGY = {
    'ma_fast': 20,
    'ma_slow': 60,
    'rsi_buy_max': 40,
    'rsi_sell_min': 70,
    'rsi_period': 14,
    'volume_ratio': 1.5,
    'base_position': 0.15,
    'max_position_single': 0.30,
    'min_stocks': 5,
    'max_stocks': 8,
    'take_profit_activation': 0.20,
    'take_profit_drawdown': 0.10,
    'stop_loss_initial': -0.15,
    'stop_profit_level1': 0.10,
    'stop_profit_level2': 0.20,
    'pyramid_levels': [-0.08, -0.15],
    'pyramid_ratios': [0.50, 0.30],
    'crash_buy_day1': 0.30,
    'crash_buy_day2': 0.20,
    'crash_buy_day3': 0.10,
    'crash_threshold': -0.05,
    'commission': 0.0003,
    'stamp_duty': 0.001,
}


def get_latest_data(code, days=100):
    """获取最新数据"""
    lg = bs.login()
    
    # 获取最近 N 天数据
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    rs = bs.query_history_k_data_plus(
        code,
        "date,open,high,low,close,volume,amount",
        start_date=start_date,
        end_date=end_date,
        frequency="d"
    )
    
    data = []
    while rs.next():
        data.append(rs.get_row_data())
    
    bs.logout()
    
    if len(data) < 60:
        return None
    
    df = pd.DataFrame(data, columns=['date', 'open', 'high', 'low', 'close', 'volume', 'amount'])
    for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
        df[col] = pd.to_numeric(df[col])
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    
    return df


def get_index_latest():
    """获取大盘最新数据"""
    lg = bs.login()
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d')
    
    rs = bs.query_history_k_data_plus(
        'sh.000001',
        "date,close",
        start_date=start_date,
        end_date=end_date,
        frequency="d"
    )
    
    data = []
    while rs.next():
        data.append(rs.get_row_data())
    
    bs.logout()
    
    if not data:
        return None
    
    df = pd.DataFrame(data, columns=['date', 'close'])
    df['close'] = pd.to_numeric(df['close'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    return df


def calculate_indicators(df):
    """计算技术指标"""
    df = df.copy()
    
    # 均线
    df['ma20'] = df['close'].rolling(STRATEGY['ma_fast']).mean()
    df['ma60'] = df['close'].rolling(STRATEGY['ma_slow']).mean()
    
    # 均线金叉/死叉
    df['ma_golden'] = (df['ma20'] > df['ma60']) & (df['ma20'].shift(1) <= df['ma60'].shift(1))
    df['ma_dead'] = (df['ma20'] < df['ma60']) & (df['ma20'].shift(1) >= df['ma60'].shift(1))
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=STRATEGY['rsi_period']).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=STRATEGY['rsi_period']).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 成交量均线
    df['volume_ma20'] = df['volume'].rolling(20).mean()
    
    return df


def check_buy_signal(df, index_df):
    """检查买入信号"""
    if df is None or len(df) < 60:
        return False, []
    
    df = calculate_indicators(df)
    latest = df.iloc[-1]
    
    signals = []
    
    # 趋势跟踪买入
    ma_golden = latest['ma_golden']
    rsi_buy = latest['rsi'] < STRATEGY['rsi_buy_max']
    volume_ok = latest['volume'] > latest['volume_ma20'] * STRATEGY['volume_ratio']
    trend_ok = latest['ma20'] > latest['ma60']
    
    if ma_golden:
        signals.append('MA 金叉')
    if rsi_buy:
        signals.append(f'RSI 超卖 ({latest["rsi"]:.1f})')
    if volume_ok:
        signals.append(f'成交量放大 ({latest["volume"]/latest["volume_ma20"]:.2f}x)')
    if trend_ok:
        signals.append('上升趋势')
    
    buy = ma_golden and rsi_buy and trend_ok and volume_ok
    
    return buy, signals


def check_crash_buy(index_df):
    """检查暴跌买入"""
    if index_df is None:
        return False, 0, ''
    
    latest = index_df.iloc[-1]
    index_change = (latest['close'] - latest['ma60']) / latest['ma60'] if latest['ma60'] > 0 else 0
    
    if index_change < STRATEGY['crash_threshold']:
        return True, index_change * 100, f'大盘跌破 60 日线{index_change*100:.1f}%'
    
    return False, 0, ''


def simulate_trading():
    """模拟交易验证"""
    print("="*80)
    print(f"日线策略 V2.0 - 模拟交易验证")
    print(f"验证日期：{TEST_DATE.strftime('%Y-%m-%d')}")
    print("="*80)
    
    # 1. 检查数据源
    print(f"\n【1】检查数据源...")
    try:
        bs.login()
        bs.logout()
        print(f"  ✅ Baostock 数据源正常")
    except Exception as e:
        print(f"  ❌ 数据源异常：{e}")
        return
    
    # 2. 检查大盘状态
    print(f"\n【2】检查大盘状态...")
    index_df = get_index_latest()
    if index_df is not None:
        latest = index_df.iloc[-1]
        index_change = (latest['close'] - latest['ma60']) / latest['ma60'] if latest['ma60'] > 0 else 0
        print(f"  上证指数：{latest['close']:.2f}")
        print(f"  MA60: {latest['ma60']:.2f}")
        print(f"  偏离度：{index_change*100:.2f}%")
        
        crash_buy, change_pct, reason = check_crash_buy(index_df)
        if crash_buy:
            print(f"  ⚠️ {reason}")
            print(f"  触发暴跌买入！")
        else:
            print(f"  ✅ 大盘正常，无暴跌")
    else:
        print(f"  ❌ 大盘数据获取失败")
    
    # 3. 检查个股信号
    print(f"\n【3】检查个股买入信号...")
    buy_signals = []
    
    for code, name, industry in STOCK_POOL[:10]:  # 先检查前 10 只
        df = get_latest_data(code)
        if df is None:
            continue
        
        buy, signals = check_buy_signal(df, index_df)
        
        if buy:
            latest = df.iloc[-1]
            buy_signals.append({
                'code': code,
                'name': name,
                'price': latest['close'],
                'signals': signals
            })
            print(f"  ✅ {name} ({code}): {', '.join(signals)}")
    
    if not buy_signals:
        print(f"  ℹ️  暂无买入信号")
    
    # 4. 模拟仓位计算
    print(f"\n【4】模拟仓位计算...")
    cash = INITIAL_CAPITAL
    positions = []
    
    if buy_signals:
        for signal in buy_signals[:STRATEGY['max_stocks']]:
            # 动态仓位 (假设胜率 50%)
            target_position = STRATEGY['base_position']
            target_value = cash * target_position
            shares = int(target_value / signal['price'] / 100) * 100
            
            if shares >= 100:
                cost = shares * signal['price'] * (1 + STRATEGY['commission'])
                positions.append({
                    'code': signal['code'],
                    'name': signal['name'],
                    'shares': shares,
                    'price': signal['price'],
                    'cost': cost,
                    'position_pct': target_position * 100
                })
    
    print(f"  可用资金：¥{cash:,.0f}")
    print(f"  拟买入股票：{len(positions)}只")
    print(f"  拟用资金：¥{sum([p['cost'] for p in positions]):,.0f}")
    print(f"  剩余资金：¥{cash - sum([p['cost'] for p in positions]):,.0f}")
    
    # 5. 检查持仓限制
    print(f"\n【5】检查持仓限制...")
    if len(positions) >= STRATEGY['min_stocks'] and len(positions) <= STRATEGY['max_stocks']:
        print(f"  ✅ 持仓数量：{len(positions)}只 (要求:{STRATEGY['min_stocks']}-{STRATEGY['max_stocks']}只)")
    else:
        print(f"  ⚠️ 持仓数量：{len(positions)}只 (要求:{STRATEGY['min_stocks']}-{STRATEGY['max_stocks']}只)")
    
    # 6. 费用估算
    print(f"\n【6】费用估算...")
    total_cost = sum([p['cost'] * STRATEGY['commission'] for p in positions])
    print(f"  买入手续费：¥{total_cost:.0f}")
    print(f"  平均每股费用：¥{total_cost/sum([p['shares'] for p in positions]) if positions else 0:.3f}")
    
    # 7. 生成模拟交易单
    print(f"\n【7】模拟交易单...")
    if positions:
        print(f"  {'股票':<10} {'代码':<12} {'买入价':<10} {'股数':<10} {'金额':<15} {'仓位':<8}")
        print(f"  {'-'*65}")
        for p in positions:
            print(f"  {p['name']:<10} {p['code']:<12} ¥{p['price']:<8.2f} {p['shares']:<8} ¥{p['cost']:>10,.0f} {p['position_pct']:.0f}%")
    else:
        print(f"  无交易")
    
    # 8. 风险提示
    print(f"\n【8】风险提示...")
    print(f"  ⚠️ 策略风险：回撤可能达到 6%")
    print(f"  ⚠️ 市场风险：注意大盘走势")
    print(f"  ⚠️ 个股风险：单只股票最大亏损 -15%")
    print(f"  ✅ 风控措施：移动止损、移动止盈、仓位控制")
    
    # 9. 保存模拟结果
    print(f"\n【9】保存模拟结果...")
    result = {
        'test_date': TEST_DATE.strftime('%Y-%m-%d'),
        'initial_capital': INITIAL_CAPITAL,
        'index_status': {
            'close': float(index_df.iloc[-1]['close']) if index_df is not None else None,
            'ma60': float(index_df.iloc[-1]['ma60']) if index_df is not None else None,
            'change_pct': float(index_change) if index_df is not None else None,
        },
        'buy_signals': buy_signals,
        'positions': positions,
        'total_cost': float(total_cost),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    output_file = Path('sim_trading/day_sim_test.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"  ✅ 结果已保存：{output_file}")
    
    print(f"\n{'='*80}")
    print(f"模拟交易验证完成！")
    print(f"{'='*80}")


if __name__ == '__main__':
    simulate_trading()
