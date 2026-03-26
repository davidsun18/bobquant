# -*- coding: utf-8 -*-
"""
模拟盘一键建仓脚本
按建议比例买入 3 只股票，50% 仓位启动
"""

import pandas as pd
import numpy as np
import baostock as bs
import json
import os
from datetime import datetime

# ==================== 配置 ====================
CONFIG = {
    'initial_capital': 50000,  # 初始资金
    'target_stocks': [
        {
            'code': 'sh.601138',
            'name': '工业富联',
            'strategy': 'macd',
            'target_percent': 0.20,  # 20% 仓位
            'reason': '强烈买入信号 - MACD 趋势跟踪'
        },
        {
            'code': 'sz.000333',
            'name': '美的集团',
            'strategy': 'bollinger',
            'target_percent': 0.15,  # 15% 仓位
            'reason': '谨慎买入信号 - 布林带均值回归'
        },
        {
            'code': 'sh.600887',
            'name': '伊利股份',
            'strategy': 'bollinger',
            'target_percent': 0.15,  # 15% 仓位
            'reason': '谨慎买入信号 - 布林带均值回归'
        }
    ],
    'stop_loss': 0.08,  # 止损 8%
    'take_profit': 0.15,  # 止盈 15%
    'output_dir': '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/'
}

# ==================== 获取最新价格 ====================
def get_current_price(code):
    """获取最新收盘价"""
    try:
        lg = bs.login()
        # 获取最近 5 天数据
        end_date = datetime.now().strftime('%Y-%m-%d')
        rs = bs.query_history_k_data_plus(
            code, 
            "date,close",
            start_date='2026-03-20',
            end_date=end_date,
            frequency="d"
        )
        data = []
        while rs.next():
            data.append(rs.get_row_data())
        bs.logout()
        
        if len(data) > 0:
            return float(data[-1][1]), data[-1][0]
    except Exception as e:
        print(f"获取 {code} 价格失败：{e}")
    
    return None, None

# ==================== 更新账户 ====================
def update_account(purchases):
    """更新账户文件"""
    account_file = f"{CONFIG['output_dir']}account.json"
    
    # 加载账户
    if os.path.exists(account_file):
        with open(account_file, 'r', encoding='utf-8') as f:
            account = json.load(f)
    else:
        account = {
            'cash': CONFIG['initial_capital'],
            'positions': {},
            'history': [],
            'start_date': datetime.now().strftime('%Y-%m-%d')
        }
    
    # 更新持仓
    for purchase in purchases:
        code = purchase['code']
        shares = purchase['shares']
        price = purchase['price']
        cost = purchase['amount']
        
        # 扣减现金
        account['cash'] -= cost
        
        # 更新持仓
        if code not in account['positions']:
            account['positions'][code] = {
                'shares': 0,
                'avg_price': 0,
                'stop_loss': price * (1 - CONFIG['stop_loss']),
                'take_profit': price * (1 + CONFIG['take_profit'])
            }
        
        # 计算新的平均成本
        old_shares = account['positions'][code]['shares']
        old_avg = account['positions'][code]['avg_price']
        
        new_shares = old_shares + shares
        new_avg = (old_shares * old_avg + shares * price) / new_shares if new_shares > 0 else 0
        
        account['positions'][code]['shares'] = new_shares
        account['positions'][code]['avg_price'] = new_avg
        
        # 记录交易
        account['history'].append({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'code': code,
            'action': '买入',
            'shares': shares,
            'price': price,
            'amount': cost,
            'reason': purchase['reason']
        })
    
    # 保存账户
    account['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(account_file, 'w', encoding='utf-8') as f:
        json.dump(account, f, ensure_ascii=False, indent=2)
    
    return account

# ==================== 生成建仓报告 ====================
def generate_report(purchases, account):
    """生成建仓报告"""
    print("\n" + "="*80)
    print("🎯 模拟盘建仓完成")
    print("="*80)
    print(f"建仓时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 买入详情
    print("\n📈 买入详情")
    print("-"*80)
    total_cost = 0
    for p in purchases:
        print(f"  🟢 {p['code']} {p['name']}")
        print(f"     数量：{p['shares']} 股")
        print(f"     价格：¥{p['price']:.2f}")
        print(f"     金额：¥{p['amount']:,.2f}")
        print(f"     仓位：{p['percent']*100:.1f}%")
        print(f"     原因：{p['reason']}")
        print(f"     止损位：¥{p['stop_loss']:.2f} (-8%)")
        print(f"     止盈位：¥{p['take_profit']:.2f} (+15%)")
        print()
        total_cost += p['amount']
    
    # 账户汇总
    print("\n📊 账户汇总")
    print("-"*80)
    print(f"  初始资金：¥{CONFIG['initial_capital']:,.2f}")
    print(f"  已用资金：¥{total_cost:,.2f}")
    print(f"  剩余现金：¥{account['cash']:,.2f}")
    print(f"  仓位比例：{total_cost/CONFIG['initial_capital']*100:.1f}%")
    
    # 持仓明细
    print("\n📈 持仓明细")
    print("-"*80)
    for code, pos in account['positions'].items():
        if pos['shares'] > 0:
            name = next((s['name'] for s in CONFIG['target_stocks'] if s['code'] == code), code)
            print(f"  {code} {name}")
            print(f"    持仓：{pos['shares']} 股")
            print(f"    成本价：¥{pos['avg_price']:.2f}")
            print(f"    止损：¥{pos['stop_loss']:.2f}")
            print(f"    止盈：¥{pos['take_profit']:.2f}")
    
    # 保存报告
    report = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'type': '建仓',
        'purchases': purchases,
        'total_cost': total_cost,
        'cash_remaining': account['cash'],
        'position_ratio': total_cost / CONFIG['initial_capital']
    }
    
    date_str = datetime.now().strftime('%Y%m%d')
    with open(f"{CONFIG['output_dir']}建仓报告_{date_str}.json", 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 生成 Markdown 报告
    md_content = f"""# 🎯 模拟盘建仓报告

## 建仓信息
- **建仓时间**: {report['date']}
- **初始资金**: ¥{CONFIG['initial_capital']:,.2f}
- **已用资金**: ¥{total_cost:,.2f}
- **剩余现金**: ¥{account['cash']:,.2f}
- **仓位比例**: {report['position_ratio']*100:.1f}%

## 买入详情

| 代码 | 名称 | 数量 | 价格 | 金额 | 仓位 | 止损 | 止盈 |
|------|------|------|------|------|------|------|------|
{chr(10).join([f"| {p['code']} | {p['name']} | {p['shares']}股 | ¥{p['price']:.2f} | ¥{p['amount']:,.2f} | {p['percent']*100:.1f}% | ¥{p['stop_loss']:.2f} | ¥{p['take_profit']:.2f} |" for p in purchases])}

## 持仓汇总
- **总持仓数**: {len(account['positions'])} 只
- **总成本**: ¥{total_cost:,.2f}
- **可用资金**: ¥{account['cash']:,.2f}

## 下一步操作
1. 每日收盘后运行 `sim_trading_system.py` 查看最新信号
2. 触及止损位立即卖出（纪律！）
3. 触及止盈位考虑分批止盈
4. 出现新信号时考虑加仓或调仓

## 风险提示
- 模拟盘仅供参考，不构成投资建议
- 严格执行止损纪律
- 不要情绪化交易
- 定期复盘总结
"""
    
    with open(f"{CONFIG['output_dir']}建仓报告_{date_str}.md", 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"\n💾 报告已保存:")
    print(f"  - {CONFIG['output_dir']}建仓报告_{date_str}.json")
    print(f"  - {CONFIG['output_dir']}建仓报告_{date_str}.md")
    print("="*80)

# ==================== 主函数 ====================
if __name__ == '__main__':
    print("="*80)
    print("🎯 模拟盘一键建仓")
    print("="*80)
    print(f"初始资金：¥{CONFIG['initial_capital']:,.2f}")
    print(f"目标股票：{len(CONFIG['target_stocks'])} 只")
    print(f"目标仓位：{sum(s['target_percent'] for s in CONFIG['target_stocks'])*100:.0f}%")
    print("="*80)
    
    # 获取价格并计算买入数量
    purchases = []
    total_cost = 0
    
    print("\n📊 获取最新价格...")
    for stock in CONFIG['target_stocks']:
        price, date = get_current_price(stock['code'])
        
        if price is None:
            print(f"  ❌ {stock['code']} {stock['name']}: 获取价格失败")
            continue
        
        # 计算目标金额
        target_amount = CONFIG['initial_capital'] * stock['target_percent']
        
        # 计算股数（100 股整数倍）
        shares = int(target_amount / price / 100) * 100
        
        # 实际金额
        actual_amount = shares * price
        
        # 检查资金是否足够
        if total_cost + actual_amount > CONFIG['initial_capital']:
            print(f"  ⚠️ {stock['name']}: 资金不足，跳过")
            continue
        
        total_cost += actual_amount
        
        purchase = {
            'code': stock['code'],
            'name': stock['name'],
            'shares': shares,
            'price': price,
            'amount': actual_amount,
            'percent': stock['target_percent'],
            'reason': stock['reason'],
            'stop_loss': price * (1 - CONFIG['stop_loss']),
            'take_profit': price * (1 + CONFIG['take_profit']),
            'date': date
        }
        
        purchases.append(purchase)
        print(f"  ✅ {stock['name']}: ¥{price:.2f} × {shares}股 = ¥{actual_amount:,.2f}")
    
    if len(purchases) == 0:
        print("\n❌ 没有成功买入任何股票")
        exit(1)
    
    # 更新账户
    print("\n📝 更新账户...")
    account = update_account(purchases)
    print("  ✅ 账户已更新")
    
    # 生成报告
    generate_report(purchases, account)
    
    print("\n" + "="*80)
    print("📚 下一步")
    print("="*80)
    print("""
✅ 建仓完成！现在你可以:

1. 查看报告:
   cat sim_trading/建仓报告_YYYYMMDD.md

2. 每日收盘后运行系统:
   python3 sim_trading_system.py

3. 生成日报:
   python3 generate_daily_report.py

4. 关注止损止盈位:
   - 触及止损立即卖出（纪律！）
   - 触及止盈考虑分批止盈

⚠️ 风险提示:
- 模拟盘仅供参考
- 严格执行纪律
- 不要情绪化交易
    """)
