# -*- coding: utf-8 -*-
"""
BobQuant 策略模块
可插拔设计：继承 BaseStrategy 并实现 check() 方法即可添加新策略
"""
from abc import ABC, abstractmethod
from datetime import datetime
from ..indicator import technical as ta
from ..core.account import get_sellable_shares


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
                reason += f' + 放量({vol_r:.1f}x)'
        # 死叉卖出
        elif latest['ma1'] < latest['ma2'] and prev['ma1'] >= prev['ma2']:
            signal = 'sell'
            reason = 'MACD 死叉'

        # RSI 过滤
        if signal == 'buy' and rsi_val > config.get('rsi_buy_max', 35):
            return {'signal': None, 'reason': f'{reason} 但RSI={rsi_val:.0f}过高', 'filtered': True}
        if signal == 'sell' and rsi_val > config.get('rsi_sell_min', 70):
            strength = 'strong'
            reason += f' + RSI超买({rsi_val:.0f})'

        # 缩量过滤
        if signal == 'buy' and config.get('volume_confirm') and strength != 'strong' and vol_r < 0.8:
            return {'signal': None, 'reason': f'{reason} 但缩量({vol_r:.1f}x)', 'filtered': True}

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
                reason += f' + 放量({vol_r:.1f}x)'
        elif bb_pos > 0.9:
            signal = 'sell'
            reason = f'布林带上轨 (%B={bb_pos:.2f})'

        if signal == 'buy' and rsi_val > config.get('rsi_buy_max', 35):
            return {'signal': None, 'reason': f'{reason} 但RSI={rsi_val:.0f}过高', 'filtered': True}
        if signal == 'sell' and rsi_val > config.get('rsi_sell_min', 70):
            strength = 'strong'
            reason += f' + RSI超买({rsi_val:.0f})'

        if signal == 'buy' and config.get('volume_confirm') and strength != 'strong' and vol_r < 0.8:
            return {'signal': None, 'reason': f'{reason} 但缩量({vol_r:.1f}x)', 'filtered': True}

        if signal:
            reason += f' RSI={rsi_val:.0f}'

        return {'signal': signal, 'reason': reason, 'strength': strength}


class GridTStrategy:
    """网格做T策略（日内高抛低吸）"""

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
                return shares, f'网格做T L{target_level} (日内+{intraday*100:.1f}%，触发{trigger*100:.1f}%)'
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
            return info['total_sold'], f'做T接回 (卖¥{last_price:.2f}→¥{current_price:.2f})'
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
        返回: {'action': 'stop_loss'/'trailing_stop'/'take_profit_LN'/None,
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
        activate = self.config.get('trailing_stop_activate', 0.05)
        drawdown = self.config.get('trailing_stop_drawdown', 0.02)
        if pnl >= activate:
            if code not in self._trailing_high or current_price > self._trailing_high[code]:
                self._trailing_high[code] = current_price
            high = self._trailing_high[code]
            dd = (high - current_price) / high
            if dd >= drawdown:
                if code in self._trailing_high:
                    del self._trailing_high[code]
                return {'action': 'trailing_stop', 'shares': sellable,
                        'reason': f'跟踪止损 (最高¥{high:.2f}→¥{current_price:.2f}，回撤{dd*100:.1f}%)',
                        'label': '🔴 跟踪止损'}

        # 3) 分批止盈
        taken = pos.get('profit_taken', 0)
        tp_levels = self.config.get('take_profit', [])
        if taken < len(tp_levels):
            tp = tp_levels[taken]
            if pnl >= tp['pct']:
                tp_shares = int(sellable * tp['sell_ratio'] / 100) * 100
                if tp_shares >= 100:
                    return {'action': f'take_profit_L{taken+1}', 'shares': tp_shares,
                            'reason': f'止盈L{taken+1} (盈{pnl*100:+.1f}% 卖{tp["sell_ratio"]*100:.0f}%)',
                            'label': f'🔴 止盈L{taken+1}'}

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
    raise ValueError(f"未知策略: {name}")
