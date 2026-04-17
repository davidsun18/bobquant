# -*- coding: utf-8 -*-
"""
BobQuant 风险过滤器 v2.0

功能：
1. ST/*ST 股票检查 - 规避退市风险
2. 流动性过滤 - 避免低成交额僵尸股
3. 高位题材股检查 - 警惕涨幅过大无业绩支撑

v2.0 新增：
- 流动性检查（日均成交额 < 5000 万剔除）
- ST 风险自动识别
- 高位股预警
"""
import pandas as pd
from datetime import datetime, timedelta


class RiskFilters:
    """风险过滤器"""
    
    def __init__(self, config):
        self.config = config
        # v2.1: 根据 Emily 建议，改为分层阈值
        self.min_turnover = config.get('min_turnover', 50000000)  # 默认 5000 万
        self.turnover_tiers = config.get('turnover_tiers', {
            'large_cap': {'min_market_cap': 50000000000, 'min_turnover': 100000000},    # 500 亿+：1 亿/日
            'mid_cap': {'min_market_cap': 10000000000, 'min_turnover': 50000000},      # 100-500 亿：5000 万/日
            'small_cap': {'min_market_cap': 0, 'min_turnover': 30000000}               # <100 亿：3000 万/日
        })
        self.max_high_gain = config.get('max_high_gain', 1.0)  # 最大涨幅 100%
        self.high_gain_period = config.get('high_gain_period', 60)  # 统计周期 60 日
    
    def check_st(self, code, name):
        """
        检查是否为 ST/*ST 股票
        
        Args:
            code: 股票代码
            name: 股票名称
            
        Returns:
            dict: {'is_st': bool, 'st_type': str, 'reason': str}
        """
        is_st = False
        st_type = ''
        reason = ''
        
        # 检查股票名称
        if name:
            if '*ST' in name:
                is_st = True
                st_type = '*ST'
                reason = f'{name} 为退市风险警示股票'
            elif 'ST' in name:
                is_st = True
                st_type = 'ST'
                reason = f'{name} 为其他风险警示股票'
        
        # 检查股票代码（创业板 ST 有特殊标识）
        if code.startswith('300') and 'ST' in name:
            is_st = True
            st_type = '创业板 ST'
            reason = f'{name} 为创业板风险警示股票'
        
        return {
            'is_st': is_st,
            'st_type': st_type,
            'reason': reason,
            'passed': not is_st
        }
    
    def estimate_market_cap(self, code, df):
        """
        估算市值（简化版：使用最新收盘价 × 总股本）
        
        实际应用中应该从数据源获取准确股本数据
        这里用简化方法：根据股价和成交量粗略估算
        """
        if df is None or len(df) == 0:
            return 0
        
        # 简化估算：假设流通股数 ≈ 成交量 × 252 (年交易日) / 换手率 (假设 50%)
        # 这是一个粗略估算，实际应用应该从数据源获取准确股本
        latest = df.iloc[-1]
        price = latest['close']
        volume = latest.get('volume', 0)
        
        # 粗略估算：日成交量 × 252 / 0.5(换手率) × 股价
        # 这个方法不准确，仅用于演示分层逻辑
        estimated_shares = volume * 252 / 0.5
        market_cap = estimated_shares * price
        
        return market_cap
    
    def get_turnover_threshold(self, code, df):
        """
        根据市值分层获取流动性阈值（Emily 建议）
        
        | 市值区间 | 建议成交额阈值 |
        |------|------|
        | ≥500 亿 | ≥1 亿/日 |
        | 100-500 亿 | ≥5000 万/日 |
        | <100 亿 | ≥3000 万/日 |
        """
        market_cap = self.estimate_market_cap(code, df)
        
        for tier_name, tier_config in self.turnover_tiers.items():
            if market_cap >= tier_config['min_market_cap']:
                return tier_config['min_turnover'], tier_name
        
        # 默认返回最小阈值
        return 30000000, 'small_cap'
    
    def check_liquidity(self, df, code):
        """
        检查流动性（日均成交额）
        
        v2.1: 根据 Emily 建议，改为分层阈值
        
        Args:
            df: DataFrame，包含 'volume' 和 'close' 列
            code: 股票代码
            
        Returns:
            dict: {'avg_turnover': float, 'passed': bool, 'reason': str}
        """
        if df is None or len(df) < 20:
            return {
                'avg_turnover': 0,
                'passed': True,  # 数据不足时暂不拦截
                'reason': '数据不足，无法判断流动性'
            }
        
        # 计算成交额 = 成交量 × 收盘价
        if 'amount' in df.columns:
            turnover = df['amount']
        elif 'volume' in df.columns and 'close' in df.columns:
            turnover = df['volume'] * df['close']
        else:
            return {
                'avg_turnover': 0,
                'passed': True,
                'reason': '无成交量数据'
            }
        
        # 计算近 20 日平均成交额
        avg_turnover = turnover.tail(20).mean()
        
        # v2.1: 根据市值分层获取阈值
        threshold, cap_tier = self.get_turnover_threshold(code, df)
        
        passed = avg_turnover >= threshold
        reason = f'近 20 日日均成交额 {avg_turnover/10000:.1f}万'
        
        if not passed:
            reason += f' < {threshold/10000:.0f}万（{cap_tier}盘，流动性不足）'
        else:
            reason += f' ≥ {threshold/10000:.0f}万（{cap_tier}盘，流动性充足）'
        
        return {
            'avg_turnover': avg_turnover,
            'passed': passed,
            'reason': reason,
            'cap_tier': cap_tier,
            'threshold': threshold
        }
    
    def check_high_gain(self, df, code):
        """
        检查是否为高位题材股（近期涨幅过大）
        
        Args:
            df: DataFrame，包含 'close' 列
            code: 股票代码
            
        Returns:
            dict: {'gain_pct': float, 'passed': bool, 'reason': str}
        """
        if df is None or len(df) < self.high_gain_period:
            return {
                'gain_pct': 0,
                'passed': True,
                'reason': '数据不足，无法判断高位风险'
            }
        
        # 计算近 N 日涨幅
        recent_close = df['close'].iloc[-1]
        period_close = df['close'].iloc[-self.high_gain_period]
        gain_pct = (recent_close - period_close) / period_close
        
        passed = gain_pct <= self.max_high_gain
        reason = f'近{self.high_gain_period}日涨幅 {gain_pct*100:.1f}%'
        
        if not passed:
            reason += f' > {self.max_high_gain*100:.0f}%（高位风险）'
        
        return {
            'gain_pct': gain_pct,
            'passed': passed,
            'reason': reason
        }
    
    def full_check(self, code, name, df):
        """
        完整风险检查
        
        Args:
            code: 股票代码
            name: 股票名称
            df: DataFrame，历史行情数据
            
        Returns:
            dict: 包含所有检查项的结果
        """
        st_result = self.check_st(code, name)
        liquidity_result = self.check_liquidity(df, code)
        high_gain_result = self.check_high_gain(df, code)
        
        all_passed = st_result['passed'] and liquidity_result['passed'] and high_gain_result['passed']
        
        return {
            'code': code,
            'name': name,
            'all_passed': all_passed,
            'st_check': st_result,
            'liquidity_check': liquidity_result,
            'high_gain_check': high_gain_result,
            'summary': self._generate_summary(st_result, liquidity_result, high_gain_result)
        }
    
    def _generate_summary(self, st, liquidity, high_gain):
        """生成检查摘要"""
        issues = []
        
        if not st['passed']:
            issues.append(f"⚠️ {st['reason']}")
        if not liquidity['passed']:
            issues.append(f"⚠️ {liquidity['reason']}")
        if not high_gain['passed']:
            issues.append(f"⚠️ {high_gain['reason']}")
        
        if issues:
            return "风险检查未通过：" + "；".join(issues)
        else:
            return "✅ 风险检查通过"


def create_risk_filters(config):
    """创建风险过滤器实例"""
    return RiskFilters(config)
