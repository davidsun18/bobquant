# -*- coding: utf-8 -*-
"""
BobQuant 分时均线做 T 策略 v2.5

核心逻辑:
- 基于 VWAP（成交量加权平均价）判断
- 股价>VWAP*1.001 → 高抛
- 股价<VWAP*0.999 → 低吸
- 不依赖持仓成本，不判断趋势
"""

def check_sell_v2_5(self, code, quote, sellable, df=None):
    """v2.5 超灵敏做 T：基于分时均线 VWAP"""
    if sellable <= 0 or quote['open'] <= 0:
        return 0, ''
    
    # 检查交易时段
    from datetime import datetime
    now = datetime.now()
    current_time = now.strftime('%H:%M')
    
    is_morning = '09:30' <= current_time <= '11:30'
    is_afternoon = '13:00' <= current_time <= '15:00'
    
    if not (is_morning or is_afternoon):
        return 0, ''  # 非交易时段不做 T
    
    # v2.5 新增：计算分时均线（VWAP）
    vwap = None
    if df is not None and 'amount' in df.columns and 'volume' in df.columns:
        today_df = df[df['volume'] > 0].tail(60)  # 取最近 60 根 K 线
        if len(today_df) > 0:
            vwap = today_df['amount'].sum() / today_df['volume'].sum()
    
    # 如果没有 VWAP 数据，用开盘价代替
    if vwap is None or vwap <= 0:
        vwap = quote['open']
    
    current = quote['current']
    info = self._state.get(code, {'sells': [], 'total_sold': 0, 'count': 0, 'bought_back': False})

    if info['bought_back'] or info['count'] >= self.config.get('t_grid_max', 12):
        return 0, ''

    target_level = info['count'] + 1
    
    # v2.5: 基于 VWAP 的触发阈值（0.1%）
    trigger_pct = self.config.get('t_grid_up', 0.001)
    trigger_price = vwap * (1 + trigger_pct)
    
    # 计算偏离度
    deviation = (current - vwap) / vwap
    
    if current >= trigger_price:
        # v2.5 优化：降低单次卖出数量，增加交易次数
        sell_ratio = self.config.get('t_sell_ratio', 0.2)  # 20% 仓位
        shares = int(sellable * sell_ratio / 100) * 100
        shares = max(shares, 100)  # 最小 100 股
        
        if shares >= 100:
            return shares, f'分时做 T L{target_level} (现价¥{current:.2f} > VWAP¥{vwap:.2f} {deviation*100:+.2f}%)'
    
    return 0, ''


def check_buyback_v2_5(self, code, current_price):
    """v2.5 超灵敏接回：基于 VWAP"""
    info = self._state.get(code)
    if not info or info['total_sold'] == 0 or info['bought_back'] or not info['sells']:
        return 0, ''

    last_price = info['sells'][-1]['price']
    
    # v2.5: 回落 0.05% 即接回（原 0.2%）
    dip = self.config.get('t_buyback_dip', 0.0005)
    
    if current_price <= last_price * (1 - dip):
        return info['total_sold'], f'分时接回 (卖¥{last_price:.2f}→¥{current_price:.2f} -{dip*100:.2f}%)'
    
    return 0, ''
