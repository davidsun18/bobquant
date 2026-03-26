#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理重复的交易记录
保留每只股票每次买入/卖出的第一条记录
"""

import json
from datetime import datetime

def deduplicate_trades():
    """去重交易记录"""
    
    # 读取交易记录
    with open('sim_trading/交易记录.json', 'r', encoding='utf-8') as f:
        trades = json.load(f)
    
    print(f'原始记录：{len(trades)} 条')
    
    # 按 代码 + 时间（精确到分钟）+ 股数 + 价格 分组
    seen = {}
    unique_trades = []
    duplicates = []
    
    for t in trades:
        # 精确到分钟的时间戳
        time_key = t.get('time', '')[:16]  # 2026-03-26 09:25
        key = f"{t['code']}|{time_key}|{t['shares']}|{t.get('price', 0)}"
        
        if key not in seen:
            seen[key] = t
            unique_trades.append(t)
        else:
            duplicates.append(t)
    
    print(f'去重后：{len(unique_trades)} 条')
    print(f'重复记录：{len(duplicates)} 条')
    
    if duplicates:
        print('\n重复记录示例:')
        for d in duplicates[:5]:
            print(f"  {d['code']}: {d['shares']}股 @ ¥{d.get('price', 0)} ({d.get('time', '')})")
        
        # 备份原文件
        backup_file = f"sim_trading/交易记录.json.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil
        shutil.copy('sim_trading/交易记录.json', backup_file)
        print(f'\n已备份：{backup_file}')
        
        # 保存去重后的文件
        with open('sim_trading/交易记录.json', 'w', encoding='utf-8') as f:
            json.dump(unique_trades, f, ensure_ascii=False, indent=2)
        
        print(f'✅ 已保存去重后的交易记录')
        
        # 同步到账户文件
        with open('sim_trading/account_ideal.json', 'r', encoding='utf-8') as f:
            account = json.load(f)
        
        account['trade_history'] = unique_trades
        
        with open('sim_trading/account_ideal.json', 'w', encoding='utf-8') as f:
            json.dump(account, f, ensure_ascii=False, indent=2)
        
        print(f'✅ 已同步到账户文件')
    else:
        print('✅ 没有重复记录')

if __name__ == '__main__':
    deduplicate_trades()
