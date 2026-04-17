# -*- coding: utf-8 -*-
"""
市场情绪分析模块 - Market Sentiment Analysis

功能：
1. 涨停/跌停比 - Limit Up/Down Ratio
2. 成交量比 - Volume Ratio
3. 涨跌家数比 - Advance/Decline Ratio
4. 北向资金流向 - Northbound Capital Flow
5. 融资融券数据 - Margin Financing Data
6. 综合情绪指数（0-100）- Composite Sentiment Index
7. 情绪阈值判断（超买/超卖）- Overbought/Oversold Detection

作者：BobQuant Team
日期：2026-04-11
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MarketSentimentAnalyzer:
    """
    市场情绪分析器
    
    计算多个情绪指标并综合为 0-100 的情绪指数
    """
    
    def __init__(self, data_provider=None):
        """
        初始化情绪分析器
        
        Args:
            data_provider: 数据提供者（可选，用于获取真实市场数据）
        """
        self.data_provider = data_provider
        self.historical_window = 60  # 历史归一化窗口（天）
        self.cache = {}  # 缓存计算结果
        
        # 情绪指标权重
        self.weights = {
            'limit_ratio': 0.25,        # 涨停/跌停比权重
            'volume_ratio': 0.20,       # 成交量比权重
            'advance_decline': 0.20,    # 涨跌家数比权重
            'northbound': 0.20,         # 北向资金权重
            'margin': 0.15              # 融资融券权重
        }
        
        # 情绪阈值
        self.thresholds = {
            'overbought': 80,   # 超买阈值
            'oversold': 20,     # 超卖阈值
            'high': 60,         # 高涨阈值
            'low': 40           # 低迷阈值
        }
    
    def calculate_all_indicators(self, date: Optional[str] = None) -> Dict:
        """
        计算所有情绪指标
        
        Args:
            date: 日期（YYYY-MM-DD 格式），默认今天
            
        Returns:
            dict: 包含所有情绪指标的字典
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # 检查缓存
        cache_key = f"{date}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 获取市场数据
        market_data = self._fetch_market_data(date)
        
        if market_data is None:
            # 使用模拟数据
            market_data = self._generate_mock_data(date)
        
        # 计算各项指标
        indicators = {}
        
        # 1. 涨停/跌停比
        indicators['limit_ratio'] = self._calculate_limit_ratio(market_data)
        
        # 2. 成交量比
        indicators['volume_ratio'] = self._calculate_volume_ratio(market_data)
        
        # 3. 涨跌家数比
        indicators['advance_decline'] = self._calculate_advance_decline(market_data)
        
        # 4. 北向资金流向
        indicators['northbound'] = self._calculate_northbound_flow(date)
        
        # 5. 融资融券数据
        indicators['margin'] = self._calculate_margin_data(date)
        
        # 6. 综合情绪指数
        composite_score = self._calculate_composite_score(indicators)
        
        # 7. 情绪等级判断
        sentiment_level = self._get_sentiment_level(composite_score)
        
        # 8. 超买/超卖判断
        market_state = self._get_market_state(composite_score)
        
        result = {
            'date': date,
            'indicators': indicators,
            'composite_score': round(composite_score, 2),
            'sentiment_level': sentiment_level,
            'market_state': market_state,
            'timestamp': datetime.now().isoformat()
        }
        
        # 缓存结果
        self.cache[cache_key] = result
        
        return result
    
    def _fetch_market_data(self, date: str) -> Optional[pd.DataFrame]:
        """
        获取市场数据
        
        Args:
            date: 日期
            
        Returns:
            DataFrame: 包含全市场股票数据的 DataFrame
        """
        try:
            if self.data_provider:
                # TODO: 集成真实数据源
                # 可以使用腾讯财经、baostock 等
                pass
            return None
        except Exception as e:
            print(f"[MarketSentiment] 获取市场数据失败：{e}")
            return None
    
    def _generate_mock_data(self, date: str) -> pd.DataFrame:
        """
        生成模拟市场数据（用于测试）
        
        Args:
            date: 日期（用于种子生成）
            
        Returns:
            DataFrame: 模拟市场数据
        """
        np.random.seed(hash(date) % 2**32)
        
        n_stocks = 5000  # A 股大约 5000 只股票
        
        # 生成基础数据
        data = {
            'code': [f'sh{600000 + i}' if i < 3000 else f'sz{1:06d}' 
                     for i in range(n_stocks)],
            'pct_change': np.random.normal(0, 2, n_stocks),  # 涨跌幅
            'volume': np.random.lognormal(10, 1, n_stocks),  # 成交量
            'prev_volume': np.random.lognormal(10, 1, n_stocks),  # 昨日成交量
            'close': np.random.uniform(5, 100, n_stocks),  # 收盘价
            'open': np.random.uniform(5, 100, n_stocks),  # 开盘价
        }
        
        df = pd.DataFrame(data)
        
        # 模拟涨跌停（±10%）
        df.loc[df['pct_change'] > 9.8, 'pct_change'] = 10.0  # 涨停
        df.loc[df['pct_change'] < -9.8, 'pct_change'] = -10.0  # 跌停
        
        return df
    
    def _calculate_limit_ratio(self, df: pd.DataFrame) -> Dict:
        """
        计算涨停/跌停比指标
        
        Args:
            df: 市场数据
            
        Returns:
            dict: {
                'limit_up_count': 涨停家数,
                'limit_down_count': 跌停家数,
                'ratio': 涨跌停比,
                'score': 该项评分（0-100）
            }
        """
        limit_up_count = len(df[df['pct_change'] >= 9.8])
        limit_down_count = len(df[df['pct_change'] <= -9.8])
        
        # 涨跌停比（涨停/跌停，至少为 0.01 避免除零）
        ratio = limit_up_count / max(limit_down_count, 1)
        
        # 转换为 0-100 评分
        # ratio > 3 得高分，ratio < 0.33 得低分
        score = 50 + 25 * np.tanh(np.log(ratio + 0.01) / 1.5)
        score = max(0, min(100, score))
        
        return {
            'limit_up_count': int(limit_up_count),
            'limit_down_count': int(limit_down_count),
            'ratio': round(ratio, 3),
            'score': round(score, 2)
        }
    
    def _calculate_volume_ratio(self, df: pd.DataFrame) -> Dict:
        """
        计算成交量比指标
        
        Args:
            df: 市场数据
            
        Returns:
            dict: {
                'avg_volume_ratio': 平均成交量比,
                'volume_expansion_rate': 放量率,
                'score': 该项评分（0-100）
            }
        """
        # 计算个股成交量比（今日/昨日）
        df['volume_ratio'] = df['volume'] / df['prev_volume'].replace(0, 1)
        
        # 平均成交量比
        avg_volume_ratio = df['volume_ratio'].mean()
        
        # 放量率（成交量比 > 1.5 的股票比例）
        volume_expansion_rate = len(df[df['volume_ratio'] > 1.5]) / len(df)
        
        # 转换为 0-100 评分
        # 成交量比在 1.2-2.0 之间较好
        if 1.2 <= avg_volume_ratio <= 2.0:
            score = 70 + 15 * (1 - abs(avg_volume_ratio - 1.6) / 0.4)
        elif avg_volume_ratio < 1.2:
            score = 40 + 30 * (avg_volume_ratio / 1.2)
        else:
            score = 70 - 20 * ((avg_volume_ratio - 2.0) / 2.0)
        
        score = max(0, min(100, score))
        
        return {
            'avg_volume_ratio': round(avg_volume_ratio, 3),
            'volume_expansion_rate': round(volume_expansion_rate, 3),
            'score': round(score, 2)
        }
    
    def _calculate_advance_decline(self, df: pd.DataFrame) -> Dict:
        """
        计算涨跌家数比指标
        
        Args:
            df: 市场数据
            
        Returns:
            dict: {
                'up_count': 上涨家数,
                'down_count': 下跌家数,
                'ratio': 涨跌比,
                'score': 该项评分（0-100）
            }
        """
        up_count = len(df[df['pct_change'] > 0])
        down_count = len(df[df['pct_change'] < 0])
        flat_count = len(df[df['pct_change'] == 0])
        
        # 涨跌比
        ratio = up_count / max(down_count, 1)
        
        # 上涨比例
        up_ratio = up_count / max(up_count + down_count, 1)
        
        # 转换为 0-100 评分
        score = up_ratio * 100
        
        return {
            'up_count': int(up_count),
            'down_count': int(down_count),
            'flat_count': int(flat_count),
            'ratio': round(ratio, 3),
            'up_ratio': round(up_ratio, 3),
            'score': round(score, 2)
        }
    
    def _calculate_northbound_flow(self, date: str) -> Dict:
        """
        计算北向资金流向指标
        
        Args:
            date: 日期
            
        Returns:
            dict: {
                'net_inflow': 净流入（亿元）,
                'inflow_trend': 流入趋势,
                'score': 该项评分（0-100）
            }
        """
        # TODO: 集成真实北向资金数据
        # 目前使用模拟数据
        
        # 模拟北向资金（基于日期生成）
        np.random.seed(hash(date + "_northbound") % 2**32)
        net_inflow = np.random.normal(20, 50)  # 平均净流入 20 亿，标准差 50 亿
        
        # 判断趋势
        if net_inflow > 50:
            trend = 'strong_inflow'  # 大幅流入
            score = 90
        elif net_inflow > 20:
            trend = 'inflow'  # 流入
            score = 70
        elif net_inflow > -20:
            trend = 'balanced'  # 平衡
            score = 50
        elif net_inflow > -50:
            trend = 'outflow'  # 流出
            score = 30
        else:
            trend = 'strong_outflow'  # 大幅流出
            score = 10
        
        return {
            'net_inflow': round(net_inflow, 2),
            'inflow_trend': trend,
            'score': round(score, 2)
        }
    
    def _calculate_margin_data(self, date: str) -> Dict:
        """
        计算融资融券数据指标
        
        Args:
            date: 日期
            
        Returns:
            dict: {
                'margin_balance': 融资余额（亿元）,
                'margin_change': 融资余额变化（亿元）,
                'margin_ratio': 融资买入比例,
                'score': 该项评分（0-100）
            }
        """
        # TODO: 集成真实融资融券数据
        # 目前使用模拟数据
        
        np.random.seed(hash(date + "_margin") % 2**32)
        
        # 模拟融资余额（万亿级别）
        margin_balance = 1.5 + np.random.normal(0, 0.1)  # 1.5 万亿左右
        margin_change = np.random.normal(0.01, 0.02)  # 变化量
        margin_ratio = 0.10 + np.random.normal(0, 0.02)  # 融资买入占比 10%
        
        # 根据融资余额变化评分
        if margin_change > 0.03:
            score = 80  # 大幅增加，情绪高涨
        elif margin_change > 0:
            score = 60  # 增加
        elif margin_change > -0.02:
            score = 50  # 基本稳定
        else:
            score = 30  # 减少
        
        return {
            'margin_balance': round(margin_balance, 4),
            'margin_change': round(margin_change, 4),
            'margin_ratio': round(margin_ratio, 4),
            'score': round(score, 2)
        }
    
    def _calculate_composite_score(self, indicators: Dict) -> float:
        """
        计算综合情绪指数
        
        Args:
            indicators: 各项指标字典
            
        Returns:
            float: 综合情绪指数（0-100）
        """
        weighted_score = 0
        
        for indicator_name, weight in self.weights.items():
            if indicator_name in indicators and 'score' in indicators[indicator_name]:
                weighted_score += indicators[indicator_name]['score'] * weight
        
        return weighted_score
    
    def _get_sentiment_level(self, score: float) -> str:
        """
        根据分数确定情绪等级
        
        Args:
            score: 情绪分数（0-100）
            
        Returns:
            str: 情绪等级
        """
        if score >= self.thresholds['overbought']:
            return 'extreme_high'  # 极度高涨
        elif score >= self.thresholds['high']:
            return 'high'  # 高涨
        elif score >= self.thresholds['low']:
            return 'neutral'  # 中性
        elif score >= self.thresholds['oversold']:
            return 'low'  # 低迷
        else:
            return 'extreme_low'  # 极度低迷
    
    def _get_market_state(self, score: float) -> Dict:
        """
        判断市场状态（超买/超卖）
        
        Args:
            score: 情绪分数
            
        Returns:
            dict: {
                'state': 'overbought'|'oversold'|'neutral',
                'signal': 'strong_sell'|'sell'|'hold'|'buy'|'strong_buy',
                'description': 描述
            }
        """
        if score >= self.thresholds['overbought']:
            return {
                'state': 'overbought',
                'signal': 'strong_sell',
                'description': '市场超买，警惕回调风险'
            }
        elif score >= self.thresholds['high']:
            return {
                'state': 'slightly_overbought',
                'signal': 'sell',
                'description': '市场偏热，谨慎参与'
            }
        elif score >= self.thresholds['low']:
            return {
                'state': 'neutral',
                'signal': 'hold',
                'description': '市场中性，正常操作'
            }
        elif score >= self.thresholds['oversold']:
            return {
                'state': 'slightly_oversold',
                'signal': 'buy',
                'description': '市场偏冷，可逐步建仓'
            }
        else:
            return {
                'state': 'oversold',
                'signal': 'strong_buy',
                'description': '市场超卖，可能是布局机会'
            }
    
    def get_position_suggestion(self, score: float, level: str) -> Dict:
        """
        根据情绪指数生成仓位建议
        
        Args:
            score: 情绪分数
            level: 情绪等级
            
        Returns:
            dict: 仓位建议
        """
        if level == 'extreme_high':
            return {
                'suggested_position': 30,
                'action': '减仓',
                'risk_level': '高',
                'reason': '市场情绪极度高涨，警惕回调风险'
            }
        elif level == 'high':
            return {
                'suggested_position': 50,
                'action': '减仓',
                'risk_level': '中高',
                'reason': '市场情绪高涨，适当降低仓位'
            }
        elif level == 'neutral':
            return {
                'suggested_position': 60,
                'action': '持有',
                'risk_level': '中',
                'reason': '市场情绪中性，维持现有仓位'
            }
        elif level == 'low':
            return {
                'suggested_position': 70,
                'action': '加仓',
                'risk_level': '中低',
                'reason': '市场情绪低迷，可逐步加仓'
            }
        else:  # extreme_low
            return {
                'suggested_position': 80,
                'action': '加仓',
                'risk_level': '低',
                'reason': '市场情绪极度低迷，可能是布局机会'
            }
    
    def generate_report(self, date: Optional[str] = None) -> str:
        """
        生成情绪分析报告
        
        Args:
            date: 日期
            
        Returns:
            str: 格式化的报告文本
        """
        result = self.calculate_all_indicators(date)
        
        report = []
        report.append("=" * 70)
        report.append("📊 BobQuant 市场情绪分析报告")
        report.append("=" * 70)
        report.append(f"日期：{result['date']}")
        report.append(f"生成时间：{result['timestamp']}")
        report.append("")
        
        # 综合情绪指数
        report.append("🎯 综合情绪指数")
        report.append("-" * 70)
        report.append(f"情绪评分：{result['composite_score']:.2f} / 100")
        report.append(f"情绪等级：{result['sentiment_level']}")
        report.append(f"市场状态：{result['market_state']['state']}")
        report.append(f"交易信号：{result['market_state']['signal']}")
        report.append(f"说明：{result['market_state']['description']}")
        report.append("")
        
        # 详细指标
        report.append("📋 详细指标")
        report.append("-" * 70)
        
        # 1. 涨停/跌停比
        lr = result['indicators']['limit_ratio']
        report.append("1️⃣ 涨停/跌停比")
        report.append(f"   涨停家数：{lr['limit_up_count']}")
        report.append(f"   跌停家数：{lr['limit_down_count']}")
        report.append(f"   涨跌停比：{lr['ratio']:.3f}")
        report.append(f"   评分：{lr['score']:.2f}")
        report.append("")
        
        # 2. 成交量比
        vr = result['indicators']['volume_ratio']
        report.append("2️⃣ 成交量比")
        report.append(f"   平均成交量比：{vr['avg_volume_ratio']:.3f}")
        report.append(f"   放量率：{vr['volume_expansion_rate']*100:.1f}%")
        report.append(f"   评分：{vr['score']:.2f}")
        report.append("")
        
        # 3. 涨跌家数比
        ad = result['indicators']['advance_decline']
        report.append("3️⃣ 涨跌家数比")
        report.append(f"   上涨家数：{ad['up_count']}")
        report.append(f"   下跌家数：{ad['down_count']}")
        report.append(f"   平盘家数：{ad['flat_count']}")
        report.append(f"   涨跌比：{ad['ratio']:.3f}")
        report.append(f"   上涨比例：{ad['up_ratio']*100:.1f}%")
        report.append(f"   评分：{ad['score']:.2f}")
        report.append("")
        
        # 4. 北向资金
        nb = result['indicators']['northbound']
        report.append("4️⃣ 北向资金流向")
        report.append(f"   净流入：{nb['net_inflow']:.2f} 亿元")
        report.append(f"   趋势：{nb['inflow_trend']}")
        report.append(f"   评分：{nb['score']:.2f}")
        report.append("")
        
        # 5. 融资融券
        mg = result['indicators']['margin']
        report.append("5️⃣ 融资融券数据")
        report.append(f"   融资余额：{mg['margin_balance']:.4f} 万亿元")
        report.append(f"   余额变化：{mg['margin_change']:.4f} 万亿元")
        report.append(f"   融资买入占比：{mg['margin_ratio']*100:.1f}%")
        report.append(f"   评分：{mg['score']:.2f}")
        report.append("")
        
        # 仓位建议
        pos = self.get_position_suggestion(result['composite_score'], result['sentiment_level'])
        report.append("💡 仓位建议")
        report.append("-" * 70)
        report.append(f"建议仓位：{pos['suggested_position']}%")
        report.append(f"操作：{pos['action']}")
        report.append(f"风险等级：{pos['risk_level']}")
        report.append(f"原因：{pos['reason']}")
        report.append("")
        
        report.append("=" * 70)
        
        return "\n".join(report)
    
    def get_sentiment_for_strategy(self, date: Optional[str] = None) -> Dict:
        """
        为策略引擎提供情绪数据接口
        
        Args:
            date: 日期
            
        Returns:
            dict: 策略引擎需要的情绪数据
        """
        result = self.calculate_all_indicators(date)
        
        return {
            'composite_score': result['composite_score'],
            'sentiment_level': result['sentiment_level'],
            'market_state': result['market_state']['state'],
            'signal': result['market_state']['signal'],
            'position_limit': self.get_position_suggestion(
                result['composite_score'], 
                result['sentiment_level']
            )['suggested_position'],
            'indicators_summary': {
                'limit_ratio_score': result['indicators']['limit_ratio']['score'],
                'volume_ratio_score': result['indicators']['volume_ratio']['score'],
                'advance_decline_score': result['indicators']['advance_decline']['score'],
                'northbound_score': result['indicators']['northbound']['score'],
                'margin_score': result['indicators']['margin']['score']
            }
        }


# 测试代码
if __name__ == '__main__':
    print("=" * 70)
    print("BobQuant 市场情绪分析模块 - 测试")
    print("=" * 70)
    
    analyzer = MarketSentimentAnalyzer()
    
    # 计算今日情绪指数
    today = datetime.now().strftime('%Y-%m-%d')
    result = analyzer.calculate_all_indicators(today)
    
    print(f"\n📊 今日情绪指数（{today}）")
    print("-" * 70)
    print(f"综合评分：{result['composite_score']:.2f} / 100")
    print(f"情绪等级：{result['sentiment_level']}")
    print(f"市场状态：{result['market_state']['state']}")
    print(f"交易信号：{result['market_state']['signal']}")
    print(f"说明：{result['market_state']['description']}")
    
    print("\n📋 核心指标:")
    indicators = result['indicators']
    print(f"  • 涨停/跌停比：{indicators['limit_ratio']['ratio']:.3f} "
          f"(涨停{indicators['limit_ratio']['limit_up_count']}家，"
          f"跌停{indicators['limit_ratio']['limit_down_count']}家)")
    print(f"  • 成交量比：{indicators['volume_ratio']['avg_volume_ratio']:.3f}")
    print(f"  • 涨跌家数比：{indicators['advance_decline']['ratio']:.3f} "
          f"(上涨{indicators['advance_decline']['up_count']}家，"
          f"下跌{indicators['advance_decline']['down_count']}家)")
    print(f"  • 北向资金：{indicators['northbound']['net_inflow']:.2f} 亿元 "
          f"({indicators['northbound']['inflow_trend']})")
    print(f"  • 融资融券：融资余额{indicators['margin']['margin_balance']:.4f} 万亿")
    
    # 生成完整报告
    print("\n" + "=" * 70)
    print("📄 完整情绪分析报告")
    print("=" * 70)
    print(analyzer.generate_report(today))
    
    # 策略接口测试
    print("\n" + "=" * 70)
    print("🔧 策略引擎接口测试")
    print("=" * 70)
    strategy_data = analyzer.get_sentiment_for_strategy(today)
    print(f"策略可用数据：")
    print(f"  - 综合评分：{strategy_data['composite_score']}")
    print(f"  - 仓位上限：{strategy_data['position_limit']}%")
    print(f"  - 交易信号：{strategy_data['signal']}")
