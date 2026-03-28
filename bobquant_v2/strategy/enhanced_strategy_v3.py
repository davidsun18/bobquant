"""
QuantaAlpha 增强策略 V3 - 修复冲突版
修复问题:
1. Volatility 逻辑错误 (elif 永不执行)
2. 市场状态被单只股票覆盖
3. RSV5 vs ROC10 信号冗余
4. 行业权重无效
5. 缺少持仓检查
"""

import sys
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

import pandas as pd
import numpy as np
from datetime import datetime
from bobquant_v2.strategy.factor_strategy import create_strategy, SignalType, Signal
from bobquant_v2.indicator.technical import all_indicators
from bobquant_v2.indicator.qa_parser import compute_alpha158_20


# ===== 全局市场状态 (避免被单只股票覆盖) =====
GLOBAL_MARKET_STATE = {
    'state': 'normal',  # normal, volatile, low_vol
    'avg_vol': 0,
    'updated_at': None,
}


def update_market_state(stock_pool_data):
    """
    更新全局市场状态
    
    Args:
        stock_pool_data: 股票池数据列表，每项包含 {'vol10': float}
    """
    if not stock_pool_data:
        return
    
    vols = [s.get('vol10', 0) * 100 for s in stock_pool_data if 'vol10' in s]
    if not vols:
        return
    
    avg_vol = np.mean(vols)
    
    if avg_vol > 15:
        GLOBAL_MARKET_STATE['state'] = 'volatile'
    elif avg_vol < 5:
        GLOBAL_MARKET_STATE['state'] = 'low_vol'
    else:
        GLOBAL_MARKET_STATE['state'] = 'normal'
    
    GLOBAL_MARKET_STATE['avg_vol'] = avg_vol
    GLOBAL_MARKET_STATE['updated_at'] = datetime.now()


def get_market_adjustment():
    """根据市场状态获取调整系数"""
    state = GLOBAL_MARKET_STATE['state']
    
    if state == 'volatile':
        return 0.7  # 高波动，降低权重
    elif state == 'low_vol':
        return 1.15  # 低波动，增加权重
    else:
        return 1.0


class EnhancedStrategyV3:
    """
    QuantaAlpha 增强策略 V3
    
    修复:
    - Volatility 逻辑 (区分适中和过高)
    - 市场状态独立计算
    - 消除因子冗余
    - 行业权重改进
    - 添加持仓检查
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        
        # 基础配置
        self.stop_loss = self.config.get('stop_loss', -0.10)
        self.take_profit = self.config.get('take_profit', 0.25)  # 降低到 25%
        
        # 信号阈值 (动态调整)
        self.base_buy_threshold = self.config.get('buy_threshold', 70)
        self.base_sell_threshold = self.config.get('sell_threshold', 40)
        
        # 行业配置 (改进版 - 调整阈值而非缩放分数)
        self.industry_thresholds = {
            '半导体': {'buy': 65, 'sell': 45},  # 降低门槛
            '科技': {'buy': 67, 'sell': 43},
            '家电': {'buy': 68, 'sell': 42},
            '有色': {'buy': 68, 'sell': 42},
            '银行': {'buy': 70, 'sell': 40},  # 基准
            '医药': {'buy': 70, 'sell': 40},
            '白酒': {'buy': 75, 'sell': 35},  # 提高门槛
            '新能源': {'buy': 78, 'sell': 32},
            '光伏': {'buy': 80, 'sell': 30},
            '锂电': {'buy': 78, 'sell': 32},
        }
        
        # 持仓记录 (避免重复买入)
        self.positions = {}
    
    def analyze(self, code, name, df, quote, industry='', position=None):
        """
        分析股票，生成信号
        
        Args:
            code: 股票代码
            name: 股票名称
            df: K 线数据
            quote: 实时行情
            industry: 所属行业
            position: 当前持仓信息 {'code': str, 'pnl': float, 'days': int}
        
        Returns:
            Signal 对象
        """
        # 计算指标
        df = all_indicators(df)
        df = compute_alpha158_20(df)
        
        latest = df.iloc[-1]
        close = latest['close']
        
        # ===== 1. 基础打分 (优化后权重) =====
        score = 50
        
        # RSV5 (权重 25，避免主导)
        if 'qa_rsv5' in latest:
            rsv5 = latest['qa_rsv5']
            if rsv5 < 0.15: score += 25
            elif rsv5 > 0.85: score -= 25
        
        # ROC10 (权重 25，与 RSV5 平衡)
        if 'qa_roc10' in latest:
            roc10 = latest['qa_roc10'] * 100
            if roc10 < -8: score += 25
            elif roc10 > 8: score -= 25
        
        # ⚠️ 移除 ROC5 (与 ROC10 冗余)
        
        # Volatility10 (修复逻辑：区分适中和过高)
        if 'qa_volatility10' in latest:
            vol10 = latest['qa_volatility10'] * 100
            if 6 < vol10 <= 12:
                score += 20  # 适中高波动加分
            elif vol10 > 12:
                score -= 15  # 过高波动减分 ⚠️ 修复
        
        # MA_Ratio (权重 20)
        if 'qa_ma_ratio5_10' in latest:
            ma_ratio = latest['qa_ma_ratio5_10'] * 100
            if ma_ratio < -2: score += 20
            elif ma_ratio > 4: score -= 20
        
        # ===== 2. 市场状态调整 (使用全局状态) =====
        market_adj = get_market_adjustment()
        score = 50 + (score - 50) * market_adj
        
        # ===== 3. 持仓检查 (避免越跌越买) =====
        if position:
            pnl = position.get('pnl', 0)
            days = position.get('days', 0)
            
            # 亏损 5% 以上，禁止买入
            if pnl < -0.05 and score >= self.base_buy_threshold:
                return Signal(
                    code, name, SignalType.HOLD, int(score),
                    [f'持仓亏损 {pnl*100:.1f}%, 禁止加仓'],
                    'medium'
                )
            
            # 持仓超过 20 天，降低卖出阈值 (避免过早卖出)
            if days > 20:
                score = score + 5  # 轻微加分，延迟卖出
        
        # ===== 4. 生成信号 =====
        reasons = []
        
        # QuantaAlpha 因子信号
        if 'qa_rsv5' in latest:
            rsv5 = latest['qa_rsv5']
            if rsv5 < 0.2: reasons.append(f'RSV5 超卖 ({rsv5:.2f})')
            elif rsv5 > 0.8: reasons.append(f'RSV5 超买 ({rsv5:.2f})')
        
        if 'qa_roc10' in latest:
            roc10 = latest['qa_roc10'] * 100
            if roc10 < -8: reasons.append(f'ROC10 超跌 ({roc10:.1f}%)')
            elif roc10 > 8: reasons.append(f'ROC10 超涨 ({roc10:.1f}%)')
        
        if 'qa_volatility10' in latest:
            vol10 = latest['qa_volatility10'] * 100
            if vol10 > 12:
                reasons.append(f'波动过高 ({vol10:.1f}%)')
            elif vol10 > 6:
                reasons.append(f'适中波动 ({vol10:.1f}%)')
        
        # 行业信号
        if industry:
            ind_config = self.industry_thresholds.get(industry)
            if ind_config:
                if ind_config['buy'] < 70:
                    reasons.append(f'行业超配 ({industry})')
                elif ind_config['buy'] > 75:
                    reasons.append(f'行业低配 ({industry})')
        
        # 市场状态信号
        if GLOBAL_MARKET_STATE['state'] == 'volatile':
            reasons.append(f'高波动市场 (avg={GLOBAL_MARKET_STATE["avg_vol"]:.1f}%)')
        elif GLOBAL_MARKET_STATE['state'] == 'low_vol':
            reasons.append(f'低波动市场 (avg={GLOBAL_MARKET_STATE["avg_vol"]:.1f}%)')
        
        # ===== 5. 确定信号类型 (使用行业阈值) =====
        buy_threshold = self.base_buy_threshold
        sell_threshold = self.base_sell_threshold
        
        if industry:
            ind_config = self.industry_thresholds.get(industry)
            if ind_config:
                buy_threshold = ind_config['buy']
                sell_threshold = ind_config['sell']
        
        # 市场状态调整阈值
        if GLOBAL_MARKET_STATE['state'] == 'volatile':
            buy_threshold += 5
            sell_threshold -= 5
        
        if score >= buy_threshold:
            signal_type = SignalType.BUY
            confidence = 'high' if score >= buy_threshold + 10 else 'medium'
        elif score >= buy_threshold - 10:
            signal_type = SignalType.BUY
            confidence = 'low'
        elif score <= sell_threshold:
            signal_type = SignalType.SELL
            confidence = 'high' if score <= sell_threshold - 10 else 'medium'
        elif score <= sell_threshold + 10:
            signal_type = SignalType.SELL
            confidence = 'low'
        else:
            signal_type = SignalType.HOLD
            confidence = 'low'
        
        return Signal(
            code=code,
            name=name,
            signal=signal_type,
            score=int(score),
            reasons=reasons,
            confidence=confidence
        )
    
    def check_stop_loss(self, buy_price, current_price, days_held):
        """
        检查止损止盈 (动态调整)
        
        Args:
            buy_price: 买入价
            current_price: 当前价
            days_held: 持仓天数
        
        Returns:
            (是否触发，原因)
        """
        if buy_price <= 0:
            return False, None
        
        pnl = (current_price - buy_price) / buy_price
        
        # 动态止损：持仓越久，止损越宽
        if days_held <= 5:
            stop_threshold = -0.10  # 短期 -10%
        elif days_held <= 15:
            stop_threshold = -0.15  # 中期 -15%
        else:
            stop_threshold = -0.20  # 长期 -20%
        
        # 动态止盈：持仓越久，止盈越宽
        if days_held <= 5:
            profit_threshold = 0.20  # 短期 +20%
        elif days_held <= 15:
            profit_threshold = 0.30  # 中期 +30%
        else:
            profit_threshold = 0.40  # 长期 +40%
        
        if pnl <= stop_threshold:
            return True, 'stop_loss'
        elif pnl >= profit_threshold:
            return True, 'take_profit'
        
        return False, None


def backtest_v3(code, name, industry, year):
    """V3 回测"""
    import baostock as bs
    
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        code, "date,open,high,low,close,volume",
        start_date=f"{year}-01-01", end_date=f"{year}-12-31", frequency="d"
    )
    
    data = []
    while (rs.error_code == '0') and rs.next():
        data.append(rs.get_row_data())
    bs.logout()
    
    if len(data) < 60:
        return None
    
    df = pd.DataFrame(data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna()
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    
    # 策略
    strategy = EnhancedStrategyV3()
    
    # 回测
    cash = 100000
    pos = 0
    in_pos = False
    buy_price = 0
    buy_date = None
    trades = []
    values = []
    
    for i in range(25, len(df)):
        date = df.index[i]
        close = df['close'].iloc[i]
        
        # 持仓信息
        position = None
        if in_pos:
            pnl = (close - buy_price) / buy_price
            days = (date - buy_date).days
            position = {'code': code, 'pnl': pnl, 'days': days}
        
        # 检查止损止盈
        if in_pos:
            stop, reason = strategy.check_stop_loss(buy_price, close, position['days'])
            if stop:
                profit = (close - buy_price) * pos
                cash += pos * close * 0.999
                trades.append({
                    'type': 'sell',
                    'date': date.strftime('%Y-%m-%d'),
                    'reason': reason,
                    'profit': profit
                })
                pos = 0
                in_pos = False
        
        # 生成信号
        try:
            signal = strategy.analyze(code, name, df.iloc[:i+1].copy(), {'current': close}, industry, position)
        except:
            continue
        
        # 交易
        if signal.signal in [SignalType.BUY, SignalType.STRONG_BUY] and not in_pos:
            shares = int(cash * 0.95 / close / 100) * 100
            if shares >= 100:
                cash -= shares * close * 1.001
                pos = shares
                in_pos = True
                buy_price = close
                buy_date = date
                trades.append({'type': 'buy', 'date': date.strftime('%Y-%m-%d'), 'score': signal.score})
        
        values.append(cash + pos * close if in_pos else cash)
    
    # 期末平仓
    if in_pos:
        cash += pos * df['close'].iloc[-1] * 0.999
    
    ret = (cash - 100000) / 100000
    
    # 胜率
    sells = [t for t in trades if t.get('type') == 'sell' and 'profit' in t]
    wins = [t for t in sells if t['profit'] > 0]
    win_rate = len(wins) / len(sells) if sells else 0
    
    # 夏普
    vals = pd.Series(values)
    rets = vals.pct_change().dropna()
    sharpe = (rets.mean() / rets.std()) * np.sqrt(252) if len(rets) > 10 and rets.std() > 0 else 0
    
    # 回撤
    roll_max = vals.expanding().max()
    dd = (vals - roll_max) / roll_max
    max_dd = abs(dd.min()) if len(dd) > 0 else 0
    
    # 止损止盈统计
    stop_losses = len([t for t in trades if t.get('reason') == 'stop_loss'])
    take_profits = len([t for t in trades if t.get('reason') == 'take_profit'])
    
    return {
        'code': code,
        'name': name,
        'industry': industry,
        'return': ret,
        'win_rate': win_rate,
        'sharpe': sharpe,
        'drawdown': max_dd,
        'trades': len(sells),
        'stop_losses': stop_losses,
        'take_profits': take_profits,
    }


if __name__ == '__main__':
    # 测试
    print("测试 V3 策略...")
    
    # 更新市场状态 (模拟)
    update_market_state([{'vol10': 0.08}, {'vol10': 0.10}, {'vol10': 0.07}])
    
    result = backtest_v3('sh.603986', '兆易创新', '半导体', 2025)
    
    if result:
        print(f"\n兆易创新 (2025):")
        print(f"  收益：{result['return']*100:.2f}%")
        print(f"  胜率：{result['win_rate']*100:.1f}%")
        print(f"  夏普：{result['sharpe']:.2f}")
        print(f"  回撤：{result['drawdown']*100:.2f}%")
        print(f"  止损：{result['stop_losses']} 次")
        print(f"  止盈：{result['take_profits']} 次")
        print(f"\n✅ V3 策略测试完成")
