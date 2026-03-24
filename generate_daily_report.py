# -*- coding: utf-8 -*-
"""
模拟盘日报生成器
生成美观的每日操作报告
"""

import pandas as pd
import json
import os
from datetime import datetime

# ==================== 配置 ====================
OUTPUT_DIR = '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/'

# ==================== 生成日报 ====================
def generate_daily_report(date_str=None):
    """生成模拟盘日报"""
    
    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')
    
    # 读取报告
    report_file = f"{OUTPUT_DIR}report_{date_str}.json"
    if not os.path.exists(report_file):
        print(f"❌ 报告不存在：{report_file}")
        return
    
    with open(report_file, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    # 读取账户信息
    account_file = f"{OUTPUT_DIR}account.json"
    with open(account_file, 'r', encoding='utf-8') as f:
        account = json.load(f)
    
    # 生成美观报告
    print("\n" + "="*80)
    print("📊 模拟盘日报")
    print("="*80)
    print(f"📅 日期：{report['date']}")
    print(f"💰 初始资金：¥50,000.00")
    print("="*80)
    
    # 今日交易
    print("\n📈 今日交易")
    print("-"*80)
    if len(report['trades']) == 0:
        print("  今日无交易")
    else:
        for trade in report['trades']:
            emoji = '🟢' if trade['操作'] == '买入' else '🔴'
            print(f"  {emoji} {trade['股票']}")
            print(f"     操作：{trade['操作']}")
            print(f"     数量：{trade['数量']} 股")
            print(f"     价格：¥{trade['价格']:.2f}")
            print(f"     金额：¥{trade['金额']:,.2f}")
            print(f"     原因：{trade['原因']}")
            print()
    
    # 账户汇总
    print("\n📊 账户汇总")
    print("-"*80)
    summary = report['summary']
    print(f"  💵 现金：¥{summary['现金']:,.2f}")
    print(f"  📈 持仓市值：¥{summary['持仓市值']:,.2f}")
    print(f"  💰 总资产：¥{summary['总资产']:,.2f}")
    print(f"  📊 总盈亏：¥{summary['总盈亏']:,.2f} ({summary['总收益率']})")
    
    # 持仓明细
    if len(summary['持仓详情']) > 0:
        print("\n📈 持仓明细")
        print("-"*80)
        print(f"  {'股票代码':<12} {'股票名称':<10} {'持仓':>8} {'成本价':>10} {'当前价':>10} {'盈亏':>12} {'盈亏%':>10}")
        print("-"*80)
        
        for pos in summary['持仓详情']:
            profit_emoji = '🟢' if pos['盈亏'] > 0 else '🔴' if pos['盈亏'] < 0 else '⚪'
            print(f"  {pos['代码']:<12} {pos['名称']:<10} {pos['持仓']:>8} "
                  f"¥{pos['成本价']:>9.2f} ¥{pos['当前价']:>9.2f} "
                  f"{profit_emoji} ¥{pos['盈亏']:>10,.2f} {pos['盈亏%']:>9}")
    
    # 扫描到的信号
    if len(report['signals']) > 0:
        print("\n🔍 今日扫描到的信号")
        print("-"*80)
        for sig in report['signals']:
            emoji = '🟢' if sig['signal'] == '买入' else '🔴' if sig['signal'] == '卖出' else '⚪'
            print(f"  {emoji} {sig['code']} {sig['name']} - {sig['signal']} ({sig['strategy']})")
            print(f"     价格：¥{sig['price']:.2f}, 原因：{sig['reason']}")
    
    # 保存为 Markdown
    md_content = f"""# 模拟盘日报 - {report['date']}

## 账户概览
| 项目 | 金额 |
|------|------|
| 初始资金 | ¥50,000.00 |
| 当前总资产 | ¥{summary['总资产']:,.2f} |
| 总盈亏 | ¥{summary['总盈亏']:,.2f} ({summary['总收益率']}) |
| 现金 | ¥{summary['现金']:,.2f} |
| 持仓市值 | ¥{summary['持仓市值']:,.2f} |

## 今日交易
{chr(10).join([f"- {t['操作']} {t['股票']} {t['数量']}股 @ ¥{t['价格']:.2f}" for t in report['trades']]) if report['trades'] else '今日无交易'}

## 持仓明细
| 代码 | 名称 | 持仓 | 成本价 | 当前价 | 盈亏 | 盈亏% |
|------|------|------|--------|--------|------|-------|
{chr(10).join([f"| {p['代码']} | {p['名称']} | {p['持仓']} | ¥{p['成本价']:.2f} | ¥{p['当前价']:.2f} | ¥{p['盈亏']:,.2f} | {p['盈亏%']} |" for p in summary['持仓详情']]) if summary['持仓详情'] else '无持仓'}

## 备注
- 本报告由量化交易系统自动生成
- 模拟盘仅供参考，不构成投资建议
- 实盘需谨慎，注意风险控制
"""
    
    md_file = f"{OUTPUT_DIR}日报_{date_str}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"\n💾 报告已保存：{md_file}")
    print("="*80)

# ==================== 主函数 ====================
if __name__ == '__main__':
    generate_daily_report()
