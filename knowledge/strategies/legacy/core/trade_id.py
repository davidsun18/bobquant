# -*- coding: utf-8 -*-
"""
BobQuant 交易标识符管理
格式：A+9 位数字 (待成交) → B+9 位数字 (已成交)
"""
import os
import json
from datetime import datetime

TRADE_ID_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'trade_counter.json')

def get_trade_id_file():
    """获取交易计数器文件路径"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, 'trade_counter.json')

def get_next_trade_id():
    """
    生成下一个交易标识符 (A+9 位数字)
    
    Returns:
        str: 交易标识符，如 A000000001
    """
    counter_file = get_trade_id_file()
    
    # 读取计数器
    counter = 0
    if os.path.exists(counter_file):
        try:
            with open(counter_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                counter = data.get('counter', 0)
        except:
            counter = 0
    
    # 生成新标识符
    counter += 1
    trade_id = f"A{counter:09d}"
    
    # 保存计数器
    with open(counter_file, 'w', encoding='utf-8') as f:
        json.dump({
            'counter': counter,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, f, indent=2, ensure_ascii=False)
    
    return trade_id

def finalize_trade_id(trade_id):
    """
    将待成交标识符 (A) 转换为已成交标识符 (B)
    
    Args:
        trade_id: 待成交标识符 (如 A000000001)
        
    Returns:
        str: 已成交标识符 (如 B000000001)
    """
    if not trade_id or not trade_id.startswith('A'):
        return trade_id
    
    # A → B
    return 'B' + trade_id[1:]

def is_valid_trade_id(trade_id):
    """
    检查标识符是否有效
    
    Args:
        trade_id: 交易标识符
        
    Returns:
        bool: 是否有效
    """
    if not trade_id or len(trade_id) != 10:
        return False
    if not trade_id[0] in ['A', 'B']:
        return False
    if not trade_id[1:].isdigit():
        return False
    return True

def get_counter():
    """获取当前交易计数器值"""
    counter_file = get_trade_id_file()
    if os.path.exists(counter_file):
        try:
            with open(counter_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('counter', 0)
        except:
            return 0
    return 0
