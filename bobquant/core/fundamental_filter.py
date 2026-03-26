# -*- coding: utf-8 -*-
"""
BobQuant 基本面筛选模块 v2.1

功能：
1. 财务指标筛选（ROE、营收增长、净利润等）
2. 估值指标筛选（PE、PB）
3. 财务健康检查（资产负债率）
4. 定期更新股票池

v2.1 新增：
- 基本面量化评分
- 行业龙头优先
- 黑名单机制
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional

try:
    import baostock as bs
except ImportError:
    pass


class FundamentalFilter:
    """基本面过滤器"""
    
    def __init__(self, config=None):
        self.config = config or {}
        
        # v2.2 更严格的基本面筛选阈值（龙头股标准）
        self.min_roe = self.config.get('min_roe', 0.12)  # ROE ≥12%
        self.min_revenue_growth = self.config.get('min_revenue_growth', 0.10)  # 营收增长≥10%
        self.min_profit_growth = self.config.get('min_profit_growth', 0.05)  # 净利润增长≥5%
        self.max_debt_ratio = self.config.get('max_debt_ratio', 0.60)  # 资产负债率≤60%
        self.max_pe = self.config.get('max_pe', 30)  # 市盈率≤30
        self.max_pb = self.config.get('max_pb', 5)  # 市净率≤5
        self.min_market_cap = self.config.get('min_market_cap', 200000000000)  # 市值≥200 亿
        
        # 黑名单（ST、问题股）
        self.blacklist = set()
        
        # 评分权重（v2.2 优化）
        self.weights = {
            'roe': 25,              # ROE 权重提高
            'revenue_growth': 20,   # 营收增长
            'profit_growth': 20,    # 净利润增长
            'debt_ratio': 10,       # 负债率
            'pe': 15,               # PE 估值
            'pb': 10                # PB 估值
        }
    
    def get_financial_data(self, code: str) -> Optional[Dict]:
        """
        获取股票财务数据
        
        Args:
            code: 股票代码
            
        Returns:
            dict: 财务指标字典
        """
        try:
            # 使用 baostock 获取财务数据
            import baostock as bs
            
            lg = bs.login()
            
            # 获取盈利能力指标
            profit_list = []
            rs_profit = bs.query_profit_data(code=code, year=2023, quarter=4)
            while (rs_profit.error_code == '0') and rs_profit.next():
                profit_list.append(rs_profit.get_row_data())
            
            # 获取成长能力指标
            growth_list = []
            rs_growth = bs.query_growth_data(code=code, year=2023, quarter=4)
            while (rs_growth.error_code == '0') and rs_growth.next():
                growth_list.append(rs_growth.get_row_data())
            
            # 获取营运能力指标
            operation_list = []
            rs_op = bs.query_operation_data(code=code, year=2023, quarter=4)
            while (rs_op.error_code == '0') and rs_op.next():
                operation_list.append(rs_op.get_row_data())
            
            bs.logout()
            
            # 解析数据
            data = {}
            
            # ROE (加权净资产收益率)
            if profit_list:
                data['roe'] = float(profit_list[0][3]) / 100 if profit_list[0][3] else 0
            
            # 营收增长率
            if growth_list:
                data['revenue_growth'] = float(growth_list[0][3]) / 100 if growth_list[0][3] else 0
            
            # 净利润增长率
            if growth_list:
                data['profit_growth'] = float(growth_list[0][4]) / 100 if growth_list[0][4] else 0
            
            # 资产负债率
            if operation_list:
                data['debt_ratio'] = float(operation_list[0][5]) / 100 if operation_list[0][5] else 0
            
            return data
            
        except Exception as e:
            print(f"  获取 {code} 财务数据失败：{e}")
            return None
    
    def get_valuation_data(self, code: str) -> Optional[Dict]:
        """
        获取估值数据（PE、PB、市值）
        
        通过实时行情获取
        """
        try:
            import baostock as bs
            
            lg = bs.login()
            
            # 获取实时行情
            rs = bs.query_stock_basic(code)
            if rs.error_code == '0':
                row = rs.get_row_data()
                # 返回：code,code_name,ipoDate,outDate,stockType,status,peTTM,pbMRQ,totalShares,limitShares
                data = {
                    'pe': float(row[6]) if row[6] else 0,
                    'pb': float(row[7]) if row[7] else 0,
                    'total_shares': float(row[8]) if row[8] else 0
                }
                
                # 获取当前股价估算市值
                price_rs = bs.query_history_k_data_plus(code, "date,close", adjustflag="3")
                if price_rs.error_code == '0' and price_rs.next():
                    close_price = float(price_rs.get_row_data()[1])
                    data['market_cap'] = data['total_shares'] * close_price
                
                bs.logout()
                return data
            
            bs.logout()
            return None
            
        except Exception as e:
            print(f"  获取 {code} 估值数据失败：{e}")
            return None
    
    def check_stock(self, code: str, name: str) -> Dict:
        """
        检查单只股票是否符合基本面标准
        
        Args:
            code: 股票代码
            name: 股票名称
            
        Returns:
            dict: 检查结果
        """
        result = {
            'code': code,
            'name': name,
            'passed': False,
            'score': 0,
            'details': {}
        }
        
        # 检查黑名单
        if name in self.blacklist or '*ST' in name or 'ST' in name:
            result['details']['blacklist'] = '股票在黑名单中'
            return result
        
        # 获取财务数据
        financial = self.get_financial_data(code)
        if financial:
            result['details'].update(financial)
        
        # 获取估值数据
        valuation = self.get_valuation_data(code)
        if valuation:
            result['details'].update(valuation)
        
        # v2.2 评分制（满分 100 分，更严格）
        score = 0
        
        # ROE 评分（25 分）- 权重提高
        roe = result['details'].get('roe', 0)
        if roe >= 0.20:
            score += 25  # 优秀
        elif roe >= 0.15:
            score += 20  # 良好
        elif roe >= 0.12:
            score += 15  # 达标
        elif roe >= 0.10:
            score += 8   # 偏低
        elif roe >= 0.05:
            score += 3   # 较差
        
        # 营收增长评分（20 分）
        rev_growth = result['details'].get('revenue_growth', 0)
        if rev_growth >= 0.30:
            score += 20  # 高增长
        elif rev_growth >= 0.20:
            score += 15  # 良好增长
        elif rev_growth >= 0.15:
            score += 10  # 稳定增长
        elif rev_growth >= 0.10:
            score += 5   # 达标
        elif rev_growth >= 0.05:
            score += 2   # 低增长
        
        # 净利润增长评分（20 分）
        profit_growth = result['details'].get('profit_growth', 0)
        if profit_growth >= 0.30:
            score += 20
        elif profit_growth >= 0.20:
            score += 15
        elif profit_growth >= 0.15:
            score += 10
        elif profit_growth >= 0.10:
            score += 5
        elif profit_growth >= 0.05:
            score += 2
        elif profit_growth >= 0:
            score += 0
        
        # 资产负债率评分（10 分）
        debt_ratio = result['details'].get('debt_ratio', 0)
        if debt_ratio <= 0.30:
            score += 10  # 非常健康
        elif debt_ratio <= 0.40:
            score += 8   # 健康
        elif debt_ratio <= 0.50:
            score += 5   # 合理
        elif debt_ratio <= 0.60:
            score += 2   # 达标
        elif debt_ratio <= 0.70:
            score += 0   # 偏高
        
        # PE 评分（15 分）
        pe = result['details'].get('pe', 0)
        if 0 < pe <= 12:
            score += 15  # 低估
        elif pe <= 18:
            score += 12  # 合理
        elif pe <= 25:
            score += 8   # 合理偏高
        elif pe <= 30:
            score += 4   # 达标
        elif pe <= 40:
            score += 0   # 偏高
        else:
            score -= 5   # 过高
        
        # PB 评分（10 分）
        pb = result['details'].get('pb', 0)
        if 0 < pb <= 2:
            score += 10  # 低估
        elif pb <= 3:
            score += 7   # 合理
        elif pb <= 4:
            score += 4   # 合理偏高
        elif pb <= 5:
            score += 2   # 达标
        else:
            score -= 3   # 过高
        
        result['score'] = score
        result['passed'] = score >= 70  # v2.2: 70 分以上通过（更严格）
        
        # 一票否决项
        if result['details'].get('roe', 0) < 0.08:  # ROE<8% 直接淘汰
            result['passed'] = False
            result['reject_reason'] = 'ROE 低于 8%'
        if result['details'].get('pe', 0) > 40:  # PE>40 直接淘汰
            result['passed'] = False
            result['reject_reason'] = 'PE 高于 40'
        
        return result
    
    def filter_stock_pool(self, stock_pool: List[Dict]) -> List[Dict]:
        """
        筛选股票池
        
        Args:
            stock_pool: 原始股票池列表
            
        Returns:
            list: 筛选后的股票池
        """
        print(f"\n🔍 开始基本面筛选...")
        print(f"   初始股票数：{len(stock_pool)}")
        
        passed_stocks = []
        failed_stocks = []
        
        for idx, stock in enumerate(stock_pool):
            code = stock['code']
            name = stock['name']
            
            # 显示进度
            if (idx + 1) % 20 == 0:
                print(f"   进度：{idx+1}/{len(stock_pool)}")
            
            result = self.check_stock(code, name)
            
            if result['passed']:
                passed_stocks.append({
                    'code': code,
                    'name': name,
                    'strategy': stock.get('strategy', 'dual_macd'),
                    'score': result['score'],
                    'fundamentals': result['details']
                })
            else:
                failed_stocks.append({
                    'code': code,
                    'name': name,
                    'reason': f"评分 {result['score']} < 60"
                })
        
        # 按评分排序
        passed_stocks.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"\n✅ 筛选完成")
        print(f"   通过：{len(passed_stocks)} 只")
        print(f"   淘汰：{len(failed_stocks)} 只")
        
        return passed_stocks
    
    def add_to_blacklist(self, name: str):
        """添加股票到黑名单"""
        self.blacklist.add(name)
        print(f"  已将 {name} 加入黑名单")


def create_fundamental_filter(config=None):
    """创建基本面过滤器实例"""
    return FundamentalFilter(config)
