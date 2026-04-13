# -*- coding: utf-8 -*-
"""
BobQuant 多因子选股策略 v1.0

实现多因子量化选股模型，包含：
1. 价值因子：PE/PB/ROE
2. 成长因子：营收增长/利润增长
3. 动量因子：20 日/60 日动量
4. 质量因子：毛利率/净利率

因子标准化和打分，筛选股票池前 10 名
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod

try:
    from ..data.provider import DataProvider, TencentProvider
except ImportError:
    from data.provider import DataProvider, TencentProvider

# BaseStrategy 在 engine.py 中定义，但我们需要避免循环导入
# 所以这里直接定义一个简单的基类接口
class BaseStrategy:
    """策略基类接口"""
    name = "base"
    
    def check(self, code, name, quote, df, pos, config):
        """检查信号方法"""
        raise NotImplementedError


# ==================== 因子计算 ====================
class FactorCalculator:
    """因子计算器"""
    
    def __init__(self, data_provider: Optional[DataProvider] = None):
        self.data_provider = data_provider or TencentProvider()
    
    def get_fundamental_data(self, code: str) -> Dict:
        """
        获取基本面数据
        
        返回：
        {
            'pe': float,      # 市盈率
            'pb': float,      # 市净率
            'roe': float,     # ROE
            'revenue_growth': float,  # 营收增长率
            'profit_growth': float,   # 利润增长率
            'gross_margin': float,    # 毛利率
            'net_margin': float,      # 净利率
        }
        """
        # 注意：这里需要从数据源获取基本面数据
        # 目前使用模拟数据，实际部署时需要接入真实数据源
        try:
            import baostock as bs
            
            # 登录
            lg = bs.login()
            
            # 获取估值指标
            code_formatted = code.replace('.', '')
            query_date = datetime.now().strftime('%Y-%m-%d')
            
            # 获取 PE/PB
            rs_pe = bs.query_valuation_data(code_formatted, query_date)
            pe_data = {}
            if rs_pe.error_code == '0' and rs_pe.next():
                pe_data = rs_pe.get_row_data()
            
            # 获取盈利能力
            rs_profit = bs.query_profit_data(code_formatted, query_date)
            profit_data = {}
            if rs_profit.error_code == '0' and rs_profit.next():
                profit_data = rs_profit.get_row_data()
            
            # 获取成长能力
            rs_growth = bs.query_growth_data(code_formatted, query_date)
            growth_data = {}
            if rs_growth.error_code == '0' and rs_growth.next():
                growth_data = rs_growth.get_row_data()
            
            bs.logout()
            
            # 解析数据
            fundamental = {
                'pe': float(pe_data[1]) if len(pe_data) > 1 and pe_data[1] else 999.0,
                'pb': float(pe_data[2]) if len(pe_data) > 2 and pe_data[2] else 999.0,
                'roe': float(profit_data[2]) if len(profit_data) > 2 and profit_data[2] else 0.0,
                'revenue_growth': float(growth_data[1]) if len(growth_data) > 1 and growth_data[1] else 0.0,
                'profit_growth': float(growth_data[2]) if len(growth_data) > 2 and growth_data[2] else 0.0,
                'gross_margin': float(profit_data[3]) if len(profit_data) > 3 and profit_data[3] else 0.0,
                'net_margin': float(profit_data[4]) if len(profit_data) > 4 and profit_data[4] else 0.0,
            }
            
            return fundamental
            
        except Exception as e:
            # 降级：返回默认值
            return {
                'pe': 999.0,
                'pb': 999.0,
                'roe': 0.0,
                'revenue_growth': 0.0,
                'profit_growth': 0.0,
                'gross_margin': 0.0,
                'net_margin': 0.0,
            }
    
    def calculate_momentum(self, df: pd.DataFrame, period: int = 20) -> float:
        """
        计算动量因子
        
        动量 = (当前收盘价 - N 日前收盘价) / N 日前收盘价 * 100%
        
        Args:
            df: 历史 K 线数据，包含 close 列
            period: 动量周期（20 或 60）
        
        Returns:
            动量值（百分比）
        """
        if df is None or len(df) < period + 1:
            return 0.0
        
        try:
            current_close = df.iloc[-1]['close']
            prev_close = df.iloc[-period]['close']
            
            if prev_close == 0:
                return 0.0
            
            momentum = (current_close - prev_close) / prev_close * 100
            return momentum
        except Exception:
            return 0.0
    
    def calculate_value_score(self, fundamental: Dict) -> float:
        """
        计算价值因子得分
        
        价值因子 = 低 PE + 低 PB + 高 ROE
        
        标准化方法：
        - PE: 越低越好，使用倒数转换
        - PB: 越低越好，使用倒数转换
        - ROE: 越高越好，直接使用
        
        Returns:
            价值因子得分（0-100）
        """
        pe = fundamental.get('pe', 999.0)
        pb = fundamental.get('pb', 999.0)
        roe = fundamental.get('roe', 0.0)
        
        # PE 得分：PE 越低得分越高，PE>100 得 0 分，PE<10 得 100 分
        if pe <= 0 or pe > 100:
            pe_score = 0.0
        else:
            pe_score = max(0, min(100, (100 - pe) * 100 / 90))
        
        # PB 得分：PB 越低得分越高，PB>10 得 0 分，PB<1 得 100 分
        if pb <= 0 or pb > 10:
            pb_score = 0.0
        else:
            pb_score = max(0, min(100, (10 - pb) * 100 / 9))
        
        # ROE 得分：ROE 越高得分越高，ROE>20 得 100 分，ROE<0 得 0 分
        roe_score = max(0, min(100, roe * 5))
        
        # 加权平均：PE 40%, PB 30%, ROE 30%
        value_score = pe_score * 0.4 + pb_score * 0.3 + roe_score * 0.3
        
        return value_score
    
    def calculate_growth_score(self, fundamental: Dict) -> float:
        """
        计算成长因子得分
        
        成长因子 = 高营收增长 + 高利润增长
        
        Returns:
            成长因子得分（0-100）
        """
        revenue_growth = fundamental.get('revenue_growth', 0.0)
        profit_growth = fundamental.get('profit_growth', 0.0)
        
        # 营收增长得分：增长率>50% 得 100 分，<0% 得 0 分
        revenue_score = max(0, min(100, revenue_growth * 2))
        
        # 利润增长得分：增长率>50% 得 100 分，<0% 得 0 分
        profit_score = max(0, min(100, profit_growth * 2))
        
        # 加权平均：营收 40%, 利润 60%（利润增长更重要）
        growth_score = revenue_score * 0.4 + profit_score * 0.6
        
        return growth_score
    
    def calculate_momentum_score(self, df: pd.DataFrame) -> float:
        """
        计算动量因子得分
        
        动量因子 = 20 日动量 * 0.6 + 60 日动量 * 0.4
        
        Returns:
            动量因子得分（0-100）
        """
        momentum_20 = self.calculate_momentum(df, period=20)
        momentum_60 = self.calculate_momentum(df, period=60)
        
        # 动量得分：动量>50% 得 100 分，<-50% 得 0 分
        momentum_20_score = max(0, min(100, (momentum_20 + 50) * 100 / 100))
        momentum_60_score = max(0, min(100, (momentum_60 + 50) * 100 / 100))
        
        # 加权平均：20 日 60%, 60 日 40%
        momentum_score = momentum_20_score * 0.6 + momentum_60_score * 0.4
        
        return momentum_score
    
    def calculate_quality_score(self, fundamental: Dict) -> float:
        """
        计算质量因子得分
        
        质量因子 = 高毛利率 + 高净利率
        
        Returns:
            质量因子得分（0-100）
        """
        gross_margin = fundamental.get('gross_margin', 0.0)
        net_margin = fundamental.get('net_margin', 0.0)
        
        # 毛利率得分：毛利率>50% 得 100 分，<0% 得 0 分
        gross_score = max(0, min(100, gross_margin * 2))
        
        # 净利率得分：净利率>30% 得 100 分，<0% 得 0 分
        net_score = max(0, min(100, net_margin * 3.33))
        
        # 加权平均：毛利率 40%, 净利率 60%
        quality_score = gross_score * 0.4 + net_score * 0.6
        
        return quality_score
    
    def calculate_total_score(self, code: str, df: pd.DataFrame, 
                             weights: Dict[str, float] = None) -> Dict:
        """
        计算股票综合得分
        
        Args:
            code: 股票代码
            df: 历史 K 线数据
            weights: 因子权重，默认 {'value': 0.3, 'growth': 0.25, 'momentum': 0.25, 'quality': 0.2}
        
        Returns:
            {
                'code': str,
                'name': str,
                'total_score': float,
                'value_score': float,
                'growth_score': float,
                'momentum_score': float,
                'quality_score': float,
                'fundamental': Dict,
                'momentum_20': float,
                'momentum_60': float,
            }
        """
        if weights is None:
            weights = {
                'value': 0.30,    # 价值因子 30%
                'growth': 0.25,   # 成长因子 25%
                'momentum': 0.25, # 动量因子 25%
                'quality': 0.20,  # 质量因子 20%
            }
        
        # 获取基本面数据
        fundamental = self.get_fundamental_data(code)
        
        # 计算各因子得分
        value_score = self.calculate_value_score(fundamental)
        growth_score = self.calculate_growth_score(fundamental)
        momentum_score = self.calculate_momentum_score(df)
        quality_score = self.calculate_quality_score(fundamental)
        
        # 计算综合得分
        total_score = (
            value_score * weights['value'] +
            growth_score * weights['growth'] +
            momentum_score * weights['momentum'] +
            quality_score * weights['quality']
        )
        
        # 获取股票名称
        name = ''
        try:
            quote = self.data_provider.get_quote(code)
            if quote:
                name = quote.get('name', '')
        except Exception:
            pass
        
        return {
            'code': code,
            'name': name,
            'total_score': round(total_score, 2),
            'value_score': round(value_score, 2),
            'growth_score': round(growth_score, 2),
            'momentum_score': round(momentum_score, 2),
            'quality_score': round(quality_score, 2),
            'fundamental': fundamental,
            'momentum_20': round(self.calculate_momentum(df, 20), 2),
            'momentum_60': round(self.calculate_momentum(df, 60), 2),
        }


# ==================== 选股引擎 ====================
class StockSelector:
    """多因子选股引擎"""
    
    def __init__(self, calculator: FactorCalculator = None, top_n: int = 10):
        self.calculator = calculator or FactorCalculator()
        self.top_n = top_n
    
    def select_stocks(self, stock_pool: List[str], 
                     weights: Dict[str, float] = None) -> List[Dict]:
        """
        从股票池中筛选得分最高的股票
        
        Args:
            stock_pool: 股票代码列表
            weights: 因子权重
        
        Returns:
            按综合得分排序的股票列表（前 top_n 名）
        """
        results = []
        
        for code in stock_pool:
            try:
                # 获取历史数据
                df = self.calculator.data_provider.get_history(code, days=60)
                
                if df is None or len(df) < 60:
                    continue
                
                # 计算得分
                score_data = self.calculator.calculate_total_score(code, df, weights)
                results.append(score_data)
                
            except Exception as e:
                print(f"计算 {code} 失败：{e}")
                continue
        
        # 按综合得分降序排序
        results.sort(key=lambda x: x['total_score'], reverse=True)
        
        # 返回前 N 名
        return results[:self.top_n]
    
    def get_stock_ranking(self, stock_pool: List[str], 
                         weights: Dict[str, float] = None) -> pd.DataFrame:
        """
        获取股票池完整排名
        
        Returns:
            DataFrame 包含所有股票的得分和排名
        """
        results = []
        
        for code in stock_pool:
            try:
                df = self.calculator.data_provider.get_history(code, days=60)
                if df is None or len(df) < 60:
                    continue
                
                score_data = self.calculator.calculate_total_score(code, df, weights)
                results.append(score_data)
                
            except Exception as e:
                print(f"计算 {code} 失败：{e}")
                continue
        
        # 转换为 DataFrame
        df_ranking = pd.DataFrame(results)
        
        if len(df_ranking) > 0:
            df_ranking['rank'] = df_ranking['total_score'].rank(ascending=False).astype(int)
            df_ranking = df_ranking.sort_values('rank')
        
        return df_ranking


# ==================== 多因子策略 ====================
class MultiFactorStrategy(BaseStrategy):
    """
    多因子选股策略
    
    基于价值、成长、动量、质量四大因子进行选股
    """
    name = "multi_factor"
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.calculator = FactorCalculator()
        self.selector = StockSelector(self.calculator, top_n=self.config.get('top_n', 10))
        
        # 因子权重配置
        self.weights = self.config.get('factor_weights', {
            'value': 0.30,
            'growth': 0.25,
            'momentum': 0.25,
            'quality': 0.20,
        })
        
        # 股票池配置
        self.stock_pool = self.config.get('stock_pool', [])
    
    def check(self, code: str, name: str, quote: dict, df: pd.DataFrame, 
              pos: dict, config: dict) -> dict:
        """
        检查个股是否符合多因子选股标准
        
        Returns:
            {
                'signal': 'buy'/'sell'/None,
                'reason': str,
                'strength': 'strong'/'normal'/'weak',
                'factor_scores': dict,
                'total_score': float,
                'rank': int,
            }
        """
        if df is None or len(df) < 60:
            return {
                'signal': None,
                'reason': '数据不足',
                'strength': 'normal',
            }
        
        # 计算该股票的因子得分
        score_data = self.calculator.calculate_total_score(code, df, self.weights)
        
        total_score = score_data['total_score']
        
        # 判断信号
        signal = None
        strength = 'normal'
        reason = ''
        
        # 得分阈值
        if total_score >= 70:
            signal = 'buy'
            strength = 'strong'
            reason = f'多因子综合得分 {total_score:.1f}（优秀）'
        elif total_score >= 55:
            signal = 'buy'
            strength = 'normal'
            reason = f'多因子综合得分 {total_score:.1f}（良好）'
        elif total_score < 30:
            signal = 'sell'
            strength = 'normal'
            reason = f'多因子综合得分 {total_score:.1f}（较差）'
        
        # 详细原因
        factor_details = []
        if score_data['value_score'] >= 70:
            factor_details.append(f"价值因子优秀 ({score_data['value_score']:.1f})")
        if score_data['growth_score'] >= 70:
            factor_details.append(f"成长因子优秀 ({score_data['growth_score']:.1f})")
        if score_data['momentum_score'] >= 70:
            factor_details.append(f"动量因子优秀 ({score_data['momentum_score']:.1f})")
        if score_data['quality_score'] >= 70:
            factor_details.append(f"质量因子优秀 ({score_data['quality_score']:.1f})")
        
        if factor_details:
            reason += ' - ' + ', '.join(factor_details)
        
        return {
            'signal': signal,
            'reason': reason,
            'strength': strength,
            'factor_scores': {
                'value': score_data['value_score'],
                'growth': score_data['growth_score'],
                'momentum': score_data['momentum_score'],
                'quality': score_data['quality_score'],
            },
            'total_score': total_score,
            'rank': score_data.get('rank', 0),
        }
    
    def get_stock_pool_ranking(self, stock_pool: List[str] = None) -> List[Dict]:
        """
        获取股票池排名
        
        Args:
            stock_pool: 股票代码列表，如果为 None 则使用配置的 stock_pool
        
        Returns:
            按综合得分排序的股票列表
        """
        pool = stock_pool or self.stock_pool
        if not pool:
            return []
        
        return self.selector.select_stocks(pool, self.weights)
    
    def update_stock_pool(self, new_pool: List[str]):
        """更新股票池"""
        self.stock_pool = new_pool
    
    def update_weights(self, new_weights: Dict[str, float]):
        """更新因子权重"""
        self.weights = new_weights


# ==================== 测试函数 ====================
def test_multi_factor_strategy():
    """测试多因子选股策略"""
    print("=" * 60)
    print("BobQuant 多因子选股策略测试")
    print("=" * 60)
    
    # 测试股票池（50 只股票示例）
    test_stock_pool = [
        'sh.600000', 'sh.600036', 'sh.600519', 'sh.601318', 'sh.601888',
        'sz.000001', 'sz.000002', 'sz.000651', 'sz.000858', 'sz.002415',
        'sh.600009', 'sh.600016', 'sh.600028', 'sh.600030', 'sh.600048',
        'sh.600050', 'sh.600104', 'sh.600276', 'sh.600309', 'sh.600346',
        'sh.600436', 'sh.600518', 'sh.600547', 'sh.600585', 'sh.600588',
        'sh.600690', 'sh.600809', 'sh.600887', 'sh.600900', 'sh.601012',
        'sh.601088', 'sh.601166', 'sh.601288', 'sh.601398', 'sh.601601',
        'sh.601628', 'sh.601668', 'sh.601688', 'sh.601766', 'sh.601857',
        'sh.601988', 'sh.601989', 'sh.603259', 'sz.000063', 'sz.000100',
        'sz.000157', 'sz.000333', 'sz.000538', 'sz.000568', 'sz.000596',
    ]
    
    # 创建选股器
    calculator = FactorCalculator()
    selector = StockSelector(calculator, top_n=10)
    
    print(f"\n测试股票池：{len(test_stock_pool)} 只股票")
    print("开始计算因子得分...\n")
    
    # 获取排名
    ranking = selector.select_stocks(test_stock_pool)
    
    if ranking:
        print("=" * 60)
        print(f"TOP 10 选股结果")
        print("=" * 60)
        print(f"{'排名':<4} {'代码':<10} {'名称':<10} {'总分':<6} {'价值':<6} {'成长':<6} {'动量':<6} {'质量':<6}")
        print("-" * 60)
        
        for i, stock in enumerate(ranking, 1):
            print(f"{i:<4} {stock['code']:<10} {stock['name']:<10} {stock['total_score']:<6.1f} "
                  f"{stock['value_score']:<6.1f} {stock['growth_score']:<6.1f} "
                  f"{stock['momentum_score']:<6.1f} {stock['quality_score']:<6.1f}")
        
        print("\n" + "=" * 60)
        print("因子计算公式说明")
        print("=" * 60)
        print("""
1. 价值因子 (30%):
   - PE 得分：(100 - PE) * 100/90, PE 范围 [10, 100]
   - PB 得分：(10 - PB) * 100/9, PB 范围 [1, 10]
   - ROE 得分：ROE * 5, ROE 范围 [0, 20]
   - 价值得分 = PE 得分*0.4 + PB 得分*0.3 + ROE 得分*0.3

2. 成长因子 (25%):
   - 营收增长得分：营收增长率 * 2, 范围 [0, 50%]
   - 利润增长得分：利润增长率 * 2, 范围 [0, 50%]
   - 成长得分 = 营收得分*0.4 + 利润得分*0.6

3. 动量因子 (25%):
   - 20 日动量：(当前价 -20 日前价)/20 日前价 * 100%
   - 60 日动量：(当前价 -60 日前价)/60 日前价 * 100%
   - 动量得分 = (20 日动量 +50)*100/100 * 0.6 + (60 日动量 +50)*100/100 * 0.4

4. 质量因子 (20%):
   - 毛利率得分：毛利率 * 2, 范围 [0, 50%]
   - 净利率得分：净利率 * 3.33, 范围 [0, 30%]
   - 质量得分 = 毛利率得分*0.4 + 净利率得分*0.6

5. 综合得分:
   - 总分 = 价值*0.30 + 成长*0.25 + 动量*0.25 + 质量*0.20
        """)
        
        print("=" * 60)
        print("与现有策略的集成方式")
        print("=" * 60)
        print("""
1. 在 strategy/engine.py 的策略工厂中注册:
   _strategy_map['multi_factor'] = MultiFactorStrategy

2. 在配置文件中启用:
   config = {
       'strategy': 'multi_factor',
       'factor_weights': {
           'value': 0.30,
           'growth': 0.25,
           'momentum': 0.25,
           'quality': 0.20,
       },
       'top_n': 10,
       'stock_pool': ['sh.600000', 'sz.000001', ...],
   }

3. 在 DecisionEngine 中添加多因子信号:
   - 调用 get_stock_pool_ranking() 获取选股结果
   - 对 TOP 10 股票执行买入逻辑
   - 对排名靠后的股票执行卖出逻辑

4. 独立选股模式:
   - 每日开盘前运行选股策略
   - 生成推荐股票池
   - 结合其他策略进行最终决策
        """)
    else:
        print("未能获取到有效的选股结果（可能是数据源问题）")
    
    print("\n测试完成!")


if __name__ == '__main__':
    test_multi_factor_strategy()
