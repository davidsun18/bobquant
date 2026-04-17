# -*- coding: utf-8 -*-
"""
股票交易规则工具
处理不同板块的交易规则差异
"""

def get_board_type(code):
    """
    判断股票所属板块
    
    Args:
        code: 股票代码 (格式：sh.600000 或 sz.300001)
        
    Returns:
        str: '主板'/'创业板'/'科创板'
    """
    # 提取数字部分
    if '.' in code:
        num_part = code.split('.')[1]
    else:
        num_part = code
    
    if num_part.startswith('688'):
        return '科创板'
    elif num_part.startswith('30'):
        return '创业板'
    elif num_part.startswith('6') or num_part.startswith('0'):
        return '主板'
    else:
        return '主板'  # 默认


def get_min_shares(code):
    """
    获取最小买入数量
    
    Args:
        code: 股票代码
        
    Returns:
        int: 最小买入数量 (股)
    """
    board = get_board_type(code)
    if board == '科创板':
        return 200
    else:  # 主板/创业板
        return 100


def get_step_size(code):
    """
    获取申报步长 (必须是此数的整数倍)
    
    Args:
        code: 股票代码
        
    Returns:
        int: 步长 (股)
    """
    board = get_board_type(code)
    if board == '科创板':
        return 1  # 超过 200 后可以 1 股递增
    else:  # 主板/创业板
        return 100


def get_max_shares(code, order_type='limit'):
    """
    获取单笔申报上限
    
    Args:
        code: 股票代码
        order_type: 'limit' (限价) 或 'market' (市价)
        
    Returns:
        int: 单笔上限 (股)
    """
    board = get_board_type(code)
    
    if board == '科创板':
        return 100000 if order_type == 'limit' else 50000
    elif board == '创业板':
        return 300000 if order_type == 'limit' else 150000
    else:  # 主板
        return 1000000


def normalize_shares(code, shares, action='buy'):
    """
    规范化股票数量 (符合板块规则)
    
    Args:
        code: 股票代码
        shares: 原始股数
        action: 'buy' 或 'sell'
        
    Returns:
        int: 规范化后的股数
    """
    min_shares = get_min_shares(code)
    step = get_step_size(code)
    max_shares = get_max_shares(code)
    
    board_type = get_board_type(code)
    
    if action == 'buy':
        # 买入规则
        if shares < min_shares:
            return min_shares
        
        if board_type == '科创板':
            return max(min_shares, min(shares, max_shares))
        else:
            normalized = int(shares / 100) * 100
            normalized = max(min_shares, normalized)
            return min(normalized, max_shares)
    
    else:  # sell
        # 卖出规则
        if shares < 100:
            return shares
        elif shares < min_shares:
            return shares
        else:
            if board_type == '科创板':
                return shares
            else:
                return int(shares / 100) * 100


# 全局变量，缓存板块类型
_board_cache = {}

def get_board_type(code):
    """获取板块类型 (带缓存)"""
    if code not in _board_cache:
        if '.' in code:
            num_part = code.split('.')[1]
        else:
            num_part = code
        
        if num_part.startswith('688'):
            _board_cache[code] = '科创板'
        elif num_part.startswith('30'):
            _board_cache[code] = '创业板'
        else:
            _board_cache[code] = '主板'
    
    return _board_cache[code]
