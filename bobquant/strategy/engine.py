# -*- coding: utf-8 -*-
"""
BobQuant 策略模块 v1.0
可插拔设计：继承 BaseStrategy 并实现 check() 方法即可添加新策略

v1.0 新增：
- ML 预测策略
- 情绪指数控制器
- 综合决策引擎
"""
from abc import ABC, abstractmethod
from datetime import datetime
try:
    from ..indicator import technical as ta
    from ..core.account import get_sellable_shares
except ImportError:
    from indicator import technical as ta
    from core.account import get_sellable_shares

from .ml_strategy import MLStrategy
from .sentiment_controller import SentimentController


class BaseStrategy(ABC):
    """策略抽象基类"""
    name = "base"

    @abstractmethod
    def check(self, code, name, quote, df, pos, config):
        """
        检查信号，返回:
          {'signal': 'buy'/'sell'/None, 'reason': str, 'strength': 'normal'/'strong'/'weak'}
        """
        pass


class MACDStrategy(BaseStrategy):
    """MACD 金叉死叉策略"""
    name = "macd"

    def check(self, code, name, quote, df, pos, config):
        if df is None or len(df) < 30:
            return {'signal': None}

        df = ta.macd(df)
        df = ta.rsi(df)
        df = ta.volume_ratio(df) if 'volume' in df.columns else df

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        rsi_val = latest.get('rsi', 50)
        vol_r = latest.get('vol_ratio', 1.0)

        signal, reason, strength = None, '', 'normal'

        # 金叉买入
        if latest['ma1'] > latest['ma2'] and prev['ma1'] <= prev['ma2']:
            signal = 'buy'
            reason = 'MACD 金叉'
            if vol_r >= config.get('volume_ratio_buy', 1.5):
                strength = 'strong'
                reason += f' + 放量 ({vol_r:.1f}x)'
        # 死叉卖出
        elif latest['ma1'] < latest['ma2'] and prev['ma1'] >= prev['ma2']:
            signal = 'sell'
            reason = 'MACD 死叉'

        # RSI 过滤
        if signal == 'buy' and rsi_val > config.get('rsi_buy_max', 35):
            return {'signal': None, 'reason': f'{reason} 但 RSI={rsi_val:.0f}过高', 'filtered': True}
        if signal == 'sell' and rsi_val > config.get('rsi_sell_min', 70):
            strength = 'strong'
            reason += f' + RSI 超买 ({rsi_val:.0f})'

        # 缩量过滤
        if signal == 'buy' and config.get('volume_confirm') and strength != 'strong' and vol_r < 0.8:
            return {'signal': None, 'reason': f'{reason} 但缩量 ({vol_r:.1f}x)', 'filtered': True}

        if signal:
            reason += f' RSI={rsi_val:.0f}'

        return {'signal': signal, 'reason': reason, 'strength': strength}


class BollingerStrategy(BaseStrategy):
    """布林带策略"""
    name = "bollinger"

    def check(self, code, name, quote, df, pos, config):
        if df is None or len(df) < 30:
            return {'signal': None}

        df = ta.bollinger(df)
        df = ta.rsi(df)
        df = ta.volume_ratio(df) if 'volume' in df.columns else df

        latest = df.iloc[-1]
        rsi_val = latest.get('rsi', 50)
        vol_r = latest.get('vol_ratio', 1.0)
        bb_pos = latest.get('bb_pos', 0.5)

        signal, reason, strength = None, '', 'normal'

        if bb_pos < 0.1:
            signal = 'buy'
            reason = f'布林带下轨 (%B={bb_pos:.2f})'
            if vol_r >= config.get('volume_ratio_buy', 1.5):
                strength = 'strong'
                reason += f' + 放量 ({vol_r:.1f}x)'
        elif bb_pos > 0.9:
            signal = 'sell'
            reason = f'布林带上轨 (%B={bb_pos:.2f})'

        if signal == 'buy' and rsi_val > config.get('rsi_buy_max', 35):
            return {'signal': None, 'reason': f'{reason} 但 RSI={rsi_val:.0f}过高', 'filtered': True}
        if signal == 'sell' and rsi_val > config.get('rsi_sell_min', 70):
            strength = 'strong'
            reason += f' + RSI 超买 ({rsi_val:.0f})'

        if signal == 'buy' and config.get('volume_confirm') and strength != 'strong' and vol_r < 0.8:
            return {'signal': None, 'reason': f'{reason} 但缩量 ({vol_r:.1f}x)', 'filtered': True}

        if signal:
            reason += f' RSI={rsi_val:.0f}'

        return {'signal': signal, 'reason': reason, 'strength': strength}


class GridTStrategy:
    """网格做 T 策略（日内高抛低吸）"""

    def __init__(self, config):
        self.config = config
        self._state = {}
        self._state_date = ''

    def reset_if_new_day(self):
        today = datetime.now().strftime('%Y-%m-%d')
        if self._state_date != today:
            self._state = {}
            self._state_date = today

    def check_sell(self, code, quote, sellable):
        """检查是否应该网格高抛，返回 (shares_to_sell, reason) 或 (0, '')"""
        if sellable <= 0 or quote['open'] <= 0:
            return 0, ''

        intraday = (quote['current'] - quote['open']) / quote['open']
        info = self._state.get(code, {'sells': [], 'total_sold': 0, 'count': 0, 'bought_back': False})

        if info['bought_back'] or info['count'] >= self.config.get('t_grid_max', 3):
            return 0, ''

        target_level = info['count'] + 1
        trigger = self.config.get('t_grid_up', 0.02) + (target_level - 1) * self.config.get('t_grid_step', 0.015)

        if intraday >= trigger:
            shares = int(sellable * self.config.get('t_sell_ratio', 0.2) / 100) * 100
            if shares >= 100:
                return shares, f'网格做 T L{target_level} (日内+{intraday*100:.1f}%，触发{trigger*100:.1f}%)'
        return 0, ''

    def record_sell(self, code, shares, price):
        info = self._state.setdefault(code, {'sells': [], 'total_sold': 0, 'count': 0, 'bought_back': False})
        info['sells'].append({'shares': shares, 'price': price})
        info['total_sold'] += shares
        info['count'] += 1

    def check_buyback(self, code, current_price):
        """检查是否应该接回，返回 (shares, reason) 或 (0, '')"""
        info = self._state.get(code)
        if not info or info['total_sold'] == 0 or info['bought_back'] or not info['sells']:
            return 0, ''

        last_price = info['sells'][-1]['price']
        dip = self.config.get('t_buyback_dip', 0.01)
        if current_price <= last_price * (1 - dip):
            return info['total_sold'], f'做 T 接回 (卖¥{last_price:.2f}→¥{current_price:.2f})'
        return 0, ''

    def record_buyback(self, code):
        if code in self._state:
            self._state[code]['bought_back'] = True


class RiskManager:
    """风控管理器（止损 + 跟踪止损 + 分批止盈）"""

    def __init__(self, config):
        self.config = config
        self._trailing_high = {}

    def check(self, code, pos, current_price):
        """
        返回：{'action': 'stop_loss'/'trailing_stop'/'take_profit_LN'/None,
               'shares': int, 'reason': str, 'label': str}
        """
        avg = pos.get('avg_price', 0)
        if avg <= 0:
            return {'action': None}

        pnl = (current_price - avg) / avg
        sellable = get_sellable_shares(pos)
        if sellable <= 0:
            return {'action': None}

        # 1) 硬止损
        if pnl <= self.config.get('stop_loss_pct', -0.08):
            return {'action': 'stop_loss', 'shares': sellable,
                    'reason': f'止损 ({pnl*100:+.1f}%)', 'label': '🔴 止损卖出'}

        # 2) 跟踪止损
        prev_high = self._trailing_high.get(code, avg)
        if current_price > prev_high:
            self._trailing_high[code] = current_price
        elif pnl >= self.config.get('trailing_activation', 0.05):
            trailing_threshold = self._trailing_high[code] * (1 - self.config.get('trailing_dip', 0.02))
            if current_price <= trailing_threshold:
                return {'action': 'trailing_stop', 'shares': sellable,
                        'reason': f'跟踪止损 (最高¥{self._trailing_high[code]:.2f}→回撤{self.config.get("trailing_dip", 0.02)*100:.0f}%)',
                        'label': '🔴 跟踪止损'}

        # 3) 分批止盈
        if pnl >= self.config.get('take_profit_start', 0.05):
            tp_levels = self.config.get('take_profit_levels', [
                {'threshold': 0.05, 'sell_ratio': 0.33},
                {'threshold': 0.10, 'sell_ratio': 0.50},
                {'threshold': 0.15, 'sell_ratio': 1.0}
            ])
            taken = 0
            for tp in tp_levels:
                if pnl >= tp['threshold']:
                    taken += 1
            if taken > 0 and taken <= len(tp_levels):
                tp = tp_levels[taken - 1]
                tp_shares = int(sellable * tp['sell_ratio'] / 100) * 100
                if tp_shares >= 100:
                    return {'action': f'take_profit_L{taken}', 'shares': tp_shares,
                            'reason': f'止盈 L{taken} (盈{pnl*100:+.1f}% 卖{tp["sell_ratio"]*100:.0f}%)',
                            'label': f'🔴 止盈 L{taken}'}

        return {'action': None}

    def clear_trailing(self, code):
        self._trailing_high.pop(code, None)


# ==================== 策略工厂 ====================
_strategy_map = {
    'macd': MACDStrategy,
    'bollinger': BollingerStrategy,
}


def get_strategy(name):
    """获取策略实例"""
    cls = _strategy_map.get(name)
    if cls:
        return cls()
    raise ValueError(f"未知策略：{name}")


# ==================== 综合决策引擎 (v1.0 NEW) ====================
class DecisionEngine:
    """
    综合决策引擎
    
    整合：
    - 技术指标信号 (MACD/布林带等)
    - ML 预测信号
    - 市场情绪指数
    
    输出最终交易决策
    """
    
    def __init__(self, config):
        self.config = config
        self.ml_strategy = MLStrategy(config) if config.get('enable_ml', False) else None
        self.sentiment_controller = SentimentController(config) if config.get('enable_sentiment', False) else None
        
        # 信号权重
        self.ml_weight = config.get('ml_signal_weight', 0.4)
        self.ta_weight = config.get('ta_signal_weight', 0.6)
        
        # 信号强度映射
        self.strength_map = {'strong': 1.0, 'normal': 0.6, 'weak': 0.3}
    
    def combine_signals(self, code, name, quote, df, pos, technical_signals):
        """
        综合多个信号源，生成最终决策
        
        Args:
            technical_signals: 技术指标信号列表 [{'signal': 'buy'/'sell'/None, 'strength': str, 'reason': str}]
            
        Returns:
            dict: {
                'signal': 'buy'/'sell'/None,
                'strength': 'strong'/'normal'/'weak',
                'reason': str,
                'confidence': float,
                'sources': dict  # 各信号源详情
            }
        """
        signals = []
        
        # 1. 技术指标信号
        for sig in technical_signals:
            if sig['signal']:
                signals.append({
                    'source': 'technical',
                    'signal': sig['signal'],
                    'strength': sig.get('strength', 'normal'),
                    'reason': sig.get('reason', '')
                })
        
        # 2. ML 预测信号
        if self.ml_strategy:
            ml_sig = self.ml_strategy.check(code, name, quote, df, pos, self.config)
            if ml_sig['signal']:
                signals.append({
                    'source': 'ml',
                    'signal': ml_sig['signal'],
                    'strength': ml_sig.get('strength', 'normal'),
                    'reason': ml_sig.get('reason', ''),
                    'ml_data': ml_sig.get('ml_data', {})
                })
        
        # 3. 如果没有信号，返回空
        if not signals:
            return {
                'signal': None,
                'strength': 'normal',
                'reason': '无有效信号',
                'confidence': 0.0,
                'sources': {'technical': [], 'ml': None}
            }
        
        # 4. 信号投票
        buy_score = 0.0
        sell_score = 0.0
        
        for sig in signals:
            weight = self.ml_weight if sig['source'] == 'ml' else (self.ta_weight / max(len([s for s in signals if s['source'] == 'technical']), 1))
            strength_val = self.strength_map.get(sig['strength'], 0.5)
            
            if sig['signal'] == 'buy':
                buy_score += weight * strength_val
            else:
                sell_score += weight * strength_val
        
        # 5. 情绪过滤（只在买入时应用）
        final_signal = None
        if buy_score > sell_score:
            # 检查情绪过滤
            if self.sentiment_controller:
                should_filter, filter_reason = self.sentiment_controller.should_filter_buy(
                    'strong' if buy_score > 0.8 else ('normal' if buy_score > 0.4 else 'weak')
                )
                if should_filter:
                    return {
                        'signal': None,
                        'strength': 'normal',
                        'reason': f"情绪过滤：{filter_reason}",
                        'confidence': 0.0,
                        'sources': {'technical': [s for s in signals if s['source'] == 'technical'], 'ml': next((s for s in signals if s['source'] == 'ml'), None)},
                        'filtered': True
                    }
            final_signal = 'buy'
        elif sell_score > buy_score:
            final_signal = 'sell'
        
        # 6. 确定最终强度
        max_score = max(buy_score, sell_score)
        if max_score >= 0.8:
            final_strength = 'strong'
        elif max_score >= 0.5:
            final_strength = 'normal'
        else:
            final_strength = 'weak'
        
        # 7. 生成原因
        reasons = [s['reason'] for s in signals if s['signal'] == final_signal]
        final_reason = ' + '.join(reasons[:3])  # 最多显示 3 个原因
        
        # 8. 调整仓位（如果是买入）
        position_adjustment = {}
        if final_signal == 'buy' and self.sentiment_controller:
            position_adjustment['position_limit'] = self.sentiment_controller.get_position_limit()
        
        return {
            'signal': final_signal,
            'strength': final_strength,
            'reason': final_reason,
            'confidence': round(max_score / (buy_score + sell_score) if (buy_score + sell_score) > 0 else 0, 2),
            'sources': {
                'technical': [s for s in signals if s['source'] == 'technical'],
                'ml': next((s for s in signals if s['source'] == 'ml'), None)
            },
            'position_adjustment': position_adjustment
        }
    
    def get_daily_report(self):
        """获取情绪日报"""
        if self.sentiment_controller:
            return self.sentiment_controller.get_daily_report()
        return "情绪指数未启用"
    
    def get_risk_warning(self):
        """获取风险预警"""
        if self.sentiment_controller:
            return self.sentiment_controller.get_risk_warning()
        return {'level': 'low', 'warnings': [], 'suggestions': []}
