"""
A 股市场情绪指数系统
参考：AI-Agent-Alpha-quantitative-trading-strategy
https://github.com/Haohao-end/AI-Agent-Alpha-quantitative-trading-strategy

功能：
- 计算市场情绪评分 (0-100)
- 基于涨跌停比、连板表现、炸板率等指标
- 提供仓位管理建议
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os

# 添加到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SentimentIndex:
    """A 股市场情绪指数计算器"""
    
    def __init__(self, data_provider=None):
        """
        初始化情绪指数计算器
        
        Args:
            data_provider: 数据提供者 (使用现有的 data.provider)
        """
        self.data_provider = data_provider
        self.historical_window = 60  # 历史归一化窗口 (天)
        self.cache = {}  # 缓存计算结果
        
    def calculate_sentiment_score(self, date: Optional[str] = None) -> Dict:
        """
        计算市场情绪评分
        
        Args:
            date: 日期 (YYYY-MM-DD 格式)，默认今天
            
        Returns:
            dict: {
                'score': 0-100 情绪分数,
                'level': 'extreme_low'|'low'|'neutral'|'high'|'extreme_high',
                'indicators': 各项指标详情,
                'position_suggestion': 仓位建议
            }
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # 检查缓存
        cache_key = f"{date}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 1. 获取市场数据
        market_data = self._fetch_market_data(date)
        
        if market_data is None or len(market_data) == 0:
            return self._default_result()
        
        # 2. 计算核心情绪指标
        indicators = self._calculate_indicators(market_data, date)
        
        # 3. 计算综合情绪分数
        raw_score = self._compute_raw_score(indicators)
        
        # 4. 历史归一化 (0-100)
        normalized_score = self._normalize_score(raw_score, date)
        
        # 5. 确定情绪等级
        level = self._get_sentiment_level(normalized_score)
        
        # 6. 生成仓位建议
        position_suggestion = self._get_position_suggestion(normalized_score, level)
        
        # 7. 检测背离信号
        divergence_warning = self._check_divergence(market_data, normalized_score)
        
        result = {
            'date': date,
            'score': round(normalized_score, 2),
            'level': level,
            'indicators': indicators,
            'position_suggestion': position_suggestion,
            'divergence_warning': divergence_warning,
            'timestamp': datetime.now().isoformat()
        }
        
        # 缓存结果
        self.cache[cache_key] = result
        
        return result
    
    def _fetch_market_data(self, date: str) -> Optional[pd.DataFrame]:
        """
        获取市场数据
        
        使用现有数据源获取全市场股票数据
        """
        try:
            # TODO: 集成现有数据源
            # 目前返回模拟数据用于测试
            return self._generate_mock_data(date)
        except Exception as e:
            print(f"[Sentiment] 获取市场数据失败：{e}")
            return None
    
    def _generate_mock_data(self, date: str) -> pd.DataFrame:
        """生成模拟市场数据 (用于测试)"""
        np.random.seed(hash(date) % 2**32)
        
        n_stocks = 5000  # A 股大约 5000 只股票
        data = {
            'code': [f'sh{600000 + i}' if i < 3000 else f'sz{1:06d}' 
                     for i in range(n_stocks)],
            'pct_change': np.random.normal(0, 2, n_stocks),  # 涨跌幅
            'volume_ratio': np.random.lognormal(0, 0.5, n_stocks),  # 量比
            'turnover_rate': np.random.lognormal(1, 0.8, n_stocks),  # 换手率
        }
        
        df = pd.DataFrame(data)
        
        # 模拟涨跌停 (±10%)
        df.loc[df['pct_change'] > 9.8, 'pct_change'] = 10.0  # 涨停
        df.loc[df['pct_change'] < -9.8, 'pct_change'] = -10.0  # 跌停
        
        return df
    
    def _calculate_indicators(self, df: pd.DataFrame, date: str) -> Dict:
        """计算各项情绪指标"""
        
        # 1. 涨跌停比
        limit_up_count = len(df[df['pct_change'] >= 9.8])
        limit_down_count = len(df[df['pct_change'] <= -9.8])
        limit_up_down_ratio = limit_up_count / max(limit_down_count, 1)
        
        # 2. 涨停股平均收益 (模拟连板表现)
        limit_up_stocks = df[df['pct_change'] >= 9.8]
        if len(limit_up_stocks) > 0:
            avg_limit_up_return = limit_up_stocks['pct_change'].mean()
        else:
            avg_limit_up_return = 0
        
        # 3. 炸板率 (模拟：从涨停回落的股票比例)
        # 简化：用接近涨停但未涨停的股票比例
        near_limit_up = len(df[(df['pct_change'] >= 7) & (df['pct_change'] < 9.5)])
        bomb_board_rate = near_limit_up / max(limit_up_count + near_limit_up, 1)
        
        # 4. 高标股溢价 (用涨幅前 10% 的股票平均收益模拟)
        top_10_pct = df['pct_change'].quantile(0.9)
        high_standard_stocks = df[df['pct_change'] >= top_10_pct]
        high_standard_premium = high_standard_stocks['pct_change'].mean() if len(high_standard_stocks) > 0 else 0
        
        # 5. 昨日涨停今日溢价 (简化：用平均涨幅模拟)
        prev_limit_up_premium = df['pct_change'].mean()
        
        # 6. 市场赚钱效应 (上涨股票比例)
        up_stocks = len(df[df['pct_change'] > 0])
        down_stocks = len(df[df['pct_change'] < 0])
        profit_effect = up_stocks / max(up_stocks + down_stocks, 1)
        
        return {
            'limit_up_count': limit_up_count,
            'limit_down_count': limit_down_count,
            'limit_up_down_ratio': round(limit_up_down_ratio, 3),
            'avg_limit_up_return': round(avg_limit_up_return, 3),
            'bomb_board_rate': round(bomb_board_rate, 3),
            'high_standard_premium': round(high_standard_premium, 3),
            'prev_limit_up_premium': round(prev_limit_up_premium, 3),
            'profit_effect': round(profit_effect, 3),
            'up_stocks': up_stocks,
            'down_stocks': down_stocks,
        }
    
    def _compute_raw_score(self, indicators: Dict) -> float:
        """
        计算原始情绪分数
        
        权重分配:
        - 涨跌停比：30%
        - 连板表现：20%
        - 炸板率：20% (反向)
        - 高标溢价：15%
        - 昨日涨停溢价：15%
        """
        score = (
            np.tanh(indicators['limit_up_down_ratio'] / 3) * 0.30 +  # 涨跌停比
            np.tanh(indicators['avg_limit_up_return'] / 5) * 0.20 +  # 连板表现
            (1 - indicators['bomb_board_rate']) * 0.20 +  # 炸板率 (反向)
            np.tanh(indicators['high_standard_premium'] / 5) * 0.15 +  # 高标溢价
            np.tanh(indicators['prev_limit_up_premium'] / 5) * 0.15  # 昨日涨停溢价
        )
        
        return score
    
    def _normalize_score(self, raw_score: float, date: str) -> float:
        """
        历史归一化到 0-100
        
        使用 60 天历史窗口计算分位数
        """
        # TODO: 实际使用时需要从历史数据计算
        # 目前简化处理：直接映射
        
        # 将 -1 到 1 的分数映射到 0-100
        normalized = (raw_score + 1) * 50
        
        # 限制在 0-100 范围
        return max(0, min(100, normalized))
    
    def _get_sentiment_level(self, score: float) -> str:
        """根据分数确定情绪等级"""
        if score >= 80:
            return 'extreme_high'  # 极度高涨 (警惕回调)
        elif score >= 60:
            return 'high'  # 高涨
        elif score >= 40:
            return 'neutral'  # 中性
        elif score >= 20:
            return 'low'  # 低迷
        else:
            return 'extreme_low'  # 极度低迷 (可能是机会)
    
    def _get_position_suggestion(self, score: float, level: str) -> Dict:
        """
        根据情绪分数生成仓位建议
        
        Returns:
            dict: {
                'suggested_position': 建议仓位 (%),
                'action': '加仓'|'减仓'|'持有'|'观望',
                'risk_level': '低'|'中'|'高'
            }
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
    
    def _check_divergence(self, df: pd.DataFrame, sentiment_score: float) -> Optional[str]:
        """
        检测背离信号
        
        例如：情绪高涨但指数下跌
        """
        # 计算市场平均涨跌幅
        avg_change = df['pct_change'].mean()
        
        # 检测背离
        if sentiment_score >= 70 and avg_change < -1:
            return "⚠️ 情绪高涨但市场下跌，警惕背离风险"
        elif sentiment_score <= 30 and avg_change > 1:
            return "💡 情绪低迷但市场上涨，可能是反转信号"
        
        return None
    
    def _default_result(self) -> Dict:
        """返回默认结果 (数据获取失败时)"""
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'score': 50,
            'level': 'neutral',
            'indicators': {},
            'position_suggestion': {
                'suggested_position': 60,
                'action': '持有',
                'risk_level': '中',
                'reason': '数据获取失败，使用默认建议'
            },
            'divergence_warning': None,
            'timestamp': datetime.now().isoformat()
        }


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("A 股市场情绪指数系统 - 测试")
    print("=" * 60)
    
    sentiment = SentimentIndex()
    result = sentiment.calculate_sentiment_score()
    
    print(f"\n📊 情绪评分：{result['score']} / 100")
    print(f"📈 情绪等级：{result['level']}")
    print(f"\n📋 核心指标:")
    
    indicators = result['indicators']
    if indicators:
        print(f"  • 涨停家数：{indicators.get('limit_up_count', 'N/A')}")
        print(f"  • 跌停家数：{indicators.get('limit_down_count', 'N/A')}")
        print(f"  • 涨跌停比：{indicators.get('limit_up_down_ratio', 'N/A')}")
        print(f"  • 炸板率：{indicators.get('bomb_board_rate', 'N/A')}")
        print(f"  • 赚钱效应：{indicators.get('profit_effect', 'N/A') * 100:.1f}%")
    
    print(f"\n💡 仓位建议:")
    pos = result['position_suggestion']
    print(f"  • 建议仓位：{pos['suggested_position']}%")
    print(f"  • 操作：{pos['action']}")
    print(f"  • 风险：{pos['risk_level']}")
    print(f"  • 原因：{pos['reason']}")
    
    if result['divergence_warning']:
        print(f"\n⚠️ 背离警告：{result['divergence_warning']}")
    
    print("\n" + "=" * 60)
