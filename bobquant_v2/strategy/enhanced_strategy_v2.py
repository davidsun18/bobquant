"""
QuantaAlpha 增强策略 V2 - 优化版
优化点：
1. 添加硬止损 (-10%)
2. 动态因子权重 (根据市场波动)
3. 行业轮动逻辑
4. 更灵敏的交易信号
"""

import sys
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

import pandas as pd
import numpy as np
from datetime import datetime
from bobquant_v2.strategy.factor_strategy import create_strategy, SignalType, Signal
from bobquant_v2.indicator.technical import all_indicators
from bobquant_v2.indicator.qa_parser import compute_alpha158_20


class EnhancedStrategy:
    """
    QuantaAlpha 增强策略 V2
    
    优化点:
    - 硬止损机制
    - 动态因子权重
    - 行业轮动
    - 更灵敏信号
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        
        # 基础配置
        self.stop_loss = self.config.get('stop_loss', -0.10)  # -10% 止损
        self.take_profit = self.config.get('take_profit', 0.30)  # +30% 止盈
        
        # 信号阈值 (更灵敏)
        self.buy_threshold = self.config.get('buy_threshold', 70)  # 从 75 降到 70
        self.sell_threshold = self.config.get('sell_threshold', 40)  # 从 35 升到 40
        
        # 行业配置
        self.industry_weights = {
            '半导体': 1.2,
            '科技': 1.1,
            '家电': 1.1,
            '银行': 1.0,
            '医药': 1.0,
            '有色': 1.1,
            '白酒': 0.8,  # 低配
            '新能源': 0.7,  # 低配
            '光伏': 0.6,  # 低配
            '锂电': 0.7,
        }
        
        # 市场状态
        self.market_state = 'normal'  # normal, volatile, bear
        
        # 动态行业权重（根据市场热点调整）
        self.industry_momentum = {}  # 行业动量评分
    
    def analyze(self, code, name, df, quote, industry=''):
        """
        分析股票，生成信号
        
        Args:
            code: 股票代码
            name: 股票名称
            df: K 线数据
            quote: 实时行情
            industry: 所属行业
        
        Returns:
            Signal 对象
        """
        # 计算指标
        df = all_indicators(df)
        df = compute_alpha158_20(df)
        
        latest = df.iloc[-1]
        close = latest['close']
        
        # ===== 1. 基础打分 (QuantaAlpha 因子) =====
        score = 50
        
        # RSV5 (权重 25)
        if 'qa_rsv5' in latest:
            rsv5 = latest['qa_rsv5']
            if rsv5 < 0.15: score += 30  # 更灵敏
            elif rsv5 > 0.85: score -= 30
        
        # ROC10 (权重 30)
        if 'qa_roc10' in latest:
            roc10 = latest['qa_roc10'] * 100
            if roc10 < -8: score += 35  # 阈值放宽
            elif roc10 > 8: score -= 35
        
        # ROC5 (权重 15)
        if 'qa_roc5' in latest:
            roc5 = latest['qa_roc5'] * 100
            if roc5 < -6: score += 20
            elif roc5 > 6: score -= 20
        
        # Volatility10 (权重 20)
        if 'qa_volatility10' in latest:
            vol10 = latest['qa_volatility10'] * 100
            if vol10 > 6: score += 25  # 阈值降低
            elif vol10 > 12: score += 10  # 过高波动减分
        
        # MA_Ratio (权重 20)
        if 'qa_ma_ratio5_10' in latest:
            ma_ratio = latest['qa_ma_ratio5_10'] * 100
            if ma_ratio < -2: score += 25
            elif ma_ratio > 4: score -= 25
        
        # ===== 2. 行业权重调整（动态） =====
        if industry:
            ind_weight = self.get_dynamic_industry_weight(industry)
            score = 50 + (score - 50) * ind_weight
        
        # ===== 3. 市场状态调整 =====
        # 计算市场波动率 (用大盘指数或股票池平均)
        if 'qa_volatility10' in latest:
            avg_vol = latest['qa_volatility10'] * 100
            if avg_vol > 15:
                self.market_state = 'volatile'
                # 高波动市场，降低权重
                score = 50 + (score - 50) * 0.8
            elif avg_vol < 5:
                self.market_state = 'low_vol'
                # 低波动市场，增加权重
                score = 50 + (score - 50) * 1.1
        
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
            if vol10 > 8: reasons.append(f'高波动 ({vol10:.1f}%)')
        
        # 行业信号
        if industry:
            ind_weight = self.industry_weights.get(industry, 1.0)
            if ind_weight > 1.1:
                reasons.append(f'行业超配 ({industry})')
            elif ind_weight < 0.8:
                reasons.append(f'行业低配 ({industry})')
        
        # 确定信号类型
        if score >= self.buy_threshold:
            signal_type = SignalType.BUY
            confidence = 'high' if score >= 85 else 'medium'
        elif score >= self.buy_threshold - 10:
            signal_type = SignalType.BUY
            confidence = 'low'
        elif score <= self.sell_threshold:
            signal_type = SignalType.SELL
            confidence = 'high' if score <= 25 else 'medium'
        elif score <= self.sell_threshold + 10:
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
    
    def check_stop_loss(self, buy_price, current_price):
        """检查是否触发止损"""
        if buy_price <= 0:
            return False, 'stop_loss'
        
        pnl = (current_price - buy_price) / buy_price
        
        if pnl <= self.stop_loss:
            return True, 'stop_loss'
        elif pnl >= self.take_profit:
            return True, 'take_profit'
        
        return False, None
    
    def update_industry_momentum(self, industry_returns):
        """
        更新行业动量评分
        
        Args:
            industry_returns: 字典 {industry: 20 日收益率}
        """
        for industry, ret in industry_returns.items():
            # 动量评分：收益率越高，评分越高
            if ret > 0.15:  # >15%
                self.industry_momentum[industry] = 1.3
            elif ret > 0.08:  # >8%
                self.industry_momentum[industry] = 1.15
            elif ret > 0:
                self.industry_momentum[industry] = 1.0
            elif ret > -0.1:  # >-10%
                self.industry_momentum[industry] = 0.9
            else:
                self.industry_momentum[industry] = 0.7
    
    def get_dynamic_industry_weight(self, industry):
        """
        获取动态行业权重（基础权重 × 动量调整）
        
        Args:
            industry: 行业名称
        
        Returns:
            动态权重
        """
        base_weight = self.industry_weights.get(industry, 1.0)
        momentum = self.industry_momentum.get(industry, 1.0)
        return base_weight * momentum


def backtest_optimized(code, name, industry, year):
    """优化版回测"""
    import baostock as bs
    
    lg = bs.login()
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    
    rs = bs.query_history_k_data_plus(
        code, "date,open,high,low,close,volume",
        start_date=start, end_date=end, frequency="d"
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
    strategy = EnhancedStrategy()
    
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
        
        # 检查止损止盈
        if in_pos:
            stop, reason = strategy.check_stop_loss(buy_price, close)
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
            signal = strategy.analyze(code, name, df.iloc[:i+1].copy(), {'current': close}, industry)
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
        trades.append({'type': 'sell', 'date': df.index[-1].strftime('%Y-%m-%d'), 'reason': '期末'})
    
    # 计算指标
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
    
    # 止损次数
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
    # 测试单只股票
    print("测试优化策略...")
    
    result = backtest_optimized('sh.603986', '兆易创新', '半导体', 2025)
    
    if result:
        print(f"\n兆易创新 (2025):")
        print(f"  收益：{result['return']*100:.2f}%")
        print(f"  胜率：{result['win_rate']*100:.1f}%")
        print(f"  夏普：{result['sharpe']:.2f}")
        print(f"  回撤：{result['drawdown']*100:.2f}%")
        print(f"  止损：{result['stop_losses']} 次")
        print(f"  止盈：{result['take_profits']} 次")
