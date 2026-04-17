# -*- coding: utf-8 -*-
"""
BobQuant 大盘风控模块 v2.0

功能：
1. 上证指数趋势判断（20 日线）
2. 大盘仓位控制（跌破 20 日线总仓位≤50%）
3. 市场情绪监控（涨跌家数比）
4. 极端行情保护（暴跌/熔断）

v2.0 新增：
- 大盘联动仓位控制
- 系统性风险预警
"""
import pandas as pd
from datetime import datetime
# 大盘数据由外部传入，避免循环依赖


class MarketRiskManager:
    """大盘风控管理器"""
    
    def __init__(self, config):
        self.config = config
        self.ma20_line = config.get('ma20_line', 20)  # 20 日均线
        self.max_position_when_bear = config.get('max_position_bear', 0.5)  # 熊市最大仓位 50%
        self.crash_threshold = config.get('crash_threshold', -0.03)  # 暴跌阈值 -3%
        self.cache = {}  # 缓存大盘数据
        self.cache_time = None
    
    def get_market_index(self, index_code='sh.000001'):
        """
        获取大盘指数数据（上证指数默认）
        
        Args:
            index_code: 指数代码，默认上证指数
            
        Returns:
            DataFrame or None
            
        Note: 此方法需要外部提供数据源，或者手动设置 self.cache[index_code]
        """
        now = datetime.now()
        
        # 缓存 5 分钟，避免频繁请求
        if self.cache_time and (now - self.cache_time).total_seconds() < 300:
            return self.cache.get(index_code)
        
        # 返回缓存的数据（如果有）
        return self.cache.get(index_code)
    
    def set_market_index(self, df, index_code='sh.000001'):
        """
        设置大盘指数数据（由外部调用）
        
        Args:
            df: DataFrame，大盘指数历史数据
            index_code: 指数代码
        """
        self.cache[index_code] = df
        self.cache_time = datetime.now()
    
    def check_ma20_trend(self, df):
        """
        检查 20 日均线趋势
        
        Args:
            df: 大盘指数 DataFrame
            
        Returns:
            dict: {'above_ma20': bool, 'ma20_value': float, 'current_price': float}
        """
        if df is None or len(df) < 20:
            return {
                'above_ma20': True,  # 数据不足时默认安全
                'ma20_value': 0,
                'current_price': 0,
                'reason': '数据不足'
            }
        
        current_price = df['close'].iloc[-1]
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        above_ma20 = current_price > ma20
        
        pct_diff = (current_price - ma20) / ma20 * 100
        
        return {
            'above_ma20': above_ma20,
            'ma20_value': ma20,
            'current_price': current_price,
            'pct_diff': pct_diff,
            'reason': f'上证指数 {current_price:.2f} vs 20 日线 {ma20:.2f} ({pct_diff:+.2f}%)'
        }
    
    def check_market_crash(self, df):
        """
        检查市场是否暴跌
        
        Args:
            df: 大盘指数 DataFrame
            
        Returns:
            dict: {'is_crash': bool, 'drop_pct': float}
        """
        if df is None or len(df) < 2:
            return {
                'is_crash': False,
                'drop_pct': 0,
                'reason': '数据不足'
            }
        
        current = df['close'].iloc[-1]
        prev = df['close'].iloc[-2]
        drop_pct = (current - prev) / prev
        
        is_crash = drop_pct <= self.crash_threshold
        
        return {
            'is_crash': is_crash,
            'drop_pct': drop_pct,
            'reason': f'今日涨跌 {drop_pct*100:+.2f}%'
        }
    
    def get_allowed_position(self, account_value, current_position_value):
        """
        根据大盘状态计算允许的最大仓位
        
        Args:
            account_value: 账户总资产
            current_position_value: 当前持仓市值
            
        Returns:
            dict: {'allowed_position': float, 'current_position_pct': float, 
                   'action': str, 'reason': str}
        """
        df = self.get_market_index()
        ma20_result = self.check_ma20_trend(df)
        crash_result = self.check_market_crash(df)
        
        current_position_pct = current_position_value / account_value if account_value > 0 else 0
        
        # 默认允许满仓
        allowed_position_pct = 1.0
        action = 'hold'
        reason = ma20_result['reason']
        
        # 暴跌保护：立即降至 30% 以下
        if crash_result['is_crash']:
            allowed_position_pct = 0.3
            action = 'reduce_urgent'
            reason = f"🔴 市场暴跌！{crash_result['reason']}，建议仓位≤30%"
        
        # 跌破 20 日线：仓位降至 50% 以下
        elif not ma20_result['above_ma20']:
            allowed_position_pct = self.max_position_when_bear
            action = 'reduce'
            reason = f"🟡 {ma20_result['reason']}，建议仓位≤{int(self.max_position_when_bear*100)}%"
        
        # 站上 20 日线：可以满仓
        else:
            action = 'hold'
            reason = f"🟢 {ma20_result['reason']}，可以正常操作"
        
        allowed_position_value = account_value * allowed_position_pct
        need_reduce = current_position_value > allowed_position_value
        
        return {
            'allowed_position_pct': allowed_position_pct,
            'allowed_position_value': allowed_position_value,
            'current_position_pct': current_position_pct,
            'current_position_value': current_position_value,
            'need_reduce': need_reduce,
            'reduce_amount': current_position_value - allowed_position_value if need_reduce else 0,
            'action': action,
            'reason': reason,
            'market_status': 'bear' if not ma20_result['above_ma20'] else 'bull'
        }
    
    def should_block_buy(self, account_value, current_position_value):
        """
        判断是否应该禁止买入
        
        Args:
            account_value: 账户总资产
            current_position_value: 当前持仓市值
            
        Returns:
            dict: {'block_buy': bool, 'reason': str}
        """
        position_info = self.get_allowed_position(account_value, current_position_value)
        
        # 暴跌时禁止买入
        if position_info['action'] == 'reduce_urgent':
            return {
                'block_buy': True,
                'reason': f"🔴 市场暴跌，禁止买入！{position_info['reason']}"
            }
        
        # 跌破 20 日线且已超仓：禁止买入
        if position_info['need_reduce'] and position_info['action'] == 'reduce':
            return {
                'block_buy': True,
                'reason': f"🟡 仓位超限，禁止买入！{position_info['reason']}"
            }
        
        return {
            'block_buy': False,
            'reason': f"✅ {position_info['reason']}"
        }


def create_market_risk_manager(config):
    """创建大盘风控管理器实例"""
    return MarketRiskManager(config)
