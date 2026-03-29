#!/usr/bin/env python3
"""
统一模拟盘启动脚本 - 整合日线策略 + 中频交易

功能:
- 统一管理日线策略和中频交易
- 共享账户数据
- 统一风控
- 统一日志

用法:
python3 scripts/start_sim_trading.py [--all] [--day] [--medium] [--status]
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')


# ========== 配置 ==========
ACCOUNT_FILE = Path('sim_trading/account_ideal.json')
TRADE_LOG_FILE = Path('sim_trading/交易记录.json')
LOG_FILE = Path('logs/sim_trading.log')

# 中频交易配置
MF_ACCOUNT_FILE = Path('sim_trading/mf_sim_account.json')
MF_TRADE_LOG_FILE = Path('sim_trading/mf_sim_trades.json')
MF_CONFIG_FILE = Path('medium_frequency/config/mf_config.yaml')


def print_status():
    """打印系统状态"""
    print("="*70)
    print("  📊 统一模拟盘系统状态")
    print("="*70)
    
    # 加载主账户
    if ACCOUNT_FILE.exists():
        with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
            account = json.load(f)
        
        # 计算总资产
        total_position_value = 0
        for code, pos in account.get('positions', {}).items():
            total_position_value += pos['shares'] * pos.get('current_price', pos.get('avg_price', 0))
        
        total_value = account.get('cash', 0) + total_position_value
        pnl = total_value - account.get('initial_capital', 1000000)
        pnl_pct = pnl / account.get('initial_capital', 1000000) * 100
        
        print(f"\n【主账户 - 日线策略】")
        print(f"  初始资金：¥{account.get('initial_capital', 1000000):,.2f}")
        print(f"  当前现金：¥{account.get('cash', 0):,.2f}")
        print(f"  持仓市值：¥{total_position_value:,.2f}")
        print(f"  总资产：¥{total_value:,.2f}")
        print(f"  总盈亏：¥{pnl:,.2f} ({pnl_pct:.2f}%)")
        print(f"  持仓数量：{len(account.get('positions', {}))}只")
    else:
        print(f"\n❌ 主账户不存在")
    
    # 加载中频账户
    if MF_ACCOUNT_FILE.exists():
        with open(MF_ACCOUNT_FILE, 'r', encoding='utf-8') as f:
            mf_account = json.load(f)
        
        mf_pnl = mf_account.get('total_pnl', 0)
        mf_pnl_pct = mf_pnl / mf_account.get('initial_capital', 200000) * 100
        
        print(f"\n【中频账户 - 中频交易】")
        print(f"  初始资金：¥{mf_account.get('initial_capital', 200000):,.2f}")
        print(f"  当前现金：¥{mf_account.get('cash', 0):,.2f}")
        print(f"  总资产：¥{mf_account.get('total_value', 0):,.2f}")
        print(f"  总盈亏：¥{mf_pnl:,.2f} ({mf_pnl_pct:.2f}%)")
        print(f"  持仓数量：{len(mf_account.get('positions', {}))}只")
    else:
        print(f"\n❌ 中频账户不存在")
    
    # 合并统计
    print(f"\n【合并统计】")
    if ACCOUNT_FILE.exists() and MF_ACCOUNT_FILE.exists():
        combined_initial = account.get('initial_capital', 1000000) + mf_account.get('initial_capital', 200000)
        combined_value = total_value + mf_account.get('total_value', 0)
        combined_pnl = combined_value - combined_initial
        combined_pnl_pct = combined_pnl / combined_initial * 100
        
        print(f"  总初始资金：¥{combined_initial:,.2f}")
        print(f"  总总资产：¥{combined_value:,.2f}")
        print(f"  总盈亏：¥{combined_pnl:,.2f} ({combined_pnl_pct:.2f}%)")
    
    print("\n" + "="*70)


def start_day_trading():
    """启动日线策略"""
    print("="*70)
    print("  🚀 启动日线策略模拟盘")
    print("="*70)
    
    # 检查账户
    if not ACCOUNT_FILE.exists():
        print("❌ 主账户不存在，请先初始化")
        return
    
    print("✅ 日线策略已就绪")
    print(f"账户文件：{ACCOUNT_FILE}")
    print(f"日志文件：{LOG_FILE}")
    
    # 提示用户如何运行
    print("\n运行日线策略:")
    print("  python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation")


def start_medium_frequency():
    """启动中频交易"""
    print("="*70)
    print("  🚀 启动中频交易模拟盘")
    print("="*70)
    
    # 检查账户
    if not MF_ACCOUNT_FILE.exists():
        print("❌ 中频账户不存在，创建新账户...")
        from scripts.run_sim_test import create_sim_account
        create_sim_account(200000.0)
    
    print("✅ 中频交易已就绪")
    print(f"账户文件：{MF_ACCOUNT_FILE}")
    print(f"日志文件：logs/mf_sim.log")
    
    # 提示用户如何运行
    print("\n运行中频交易:")
    print("  单次检查：python3 scripts/run_sim_test.py --run --once")
    print("  循环监控：python3 scripts/run_sim_test.py --run")
    print("  后台运行：nohup python3 scripts/run_sim_test.py --run > logs/mf_sim.log 2>&1 &")


def start_all():
    """同时启动日线策略和中频交易"""
    print("="*70)
    print("  🚀 启动统一模拟盘系统")
    print("="*70)
    
    # 启动日线策略
    start_day_trading()
    
    # 启动中频交易
    start_medium_frequency()
    
    # 打印状态
    print_status()
    
    print("\n✅ 统一模拟盘系统启动完成！")
    print("\n使用说明:")
    print("  1. 日线策略：自动运行 (Cron)")
    print("  2. 中频交易：每 5 分钟检查一次")
    print("  3. 查看状态：python3 scripts/start_sim_trading.py --status")
    print("  4. 查看日志：tail -f logs/sim_trading.log")
    print("  5. 生成报告：python3 scripts/run_sim_test.py --report")


def sync_accounts():
    """同步两个账户的数据"""
    print("="*70)
    print("  🔄 同步账户数据")
    print("="*70)
    
    # 加载主账户
    if not ACCOUNT_FILE.exists():
        print("❌ 主账户不存在")
        return
    
    with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
        account = json.load(f)
    
    # 更新持仓的当前价格
    from medium_frequency.data_fetcher import MinuteDataFetcher
    fetcher = MinuteDataFetcher()
    
    print("\n更新持仓价格...")
    for code, pos in account.get('positions', {}).items():
        df = fetcher.get_minute_kline(code, period=5, limit=1)
        if df is not None and len(df) > 0:
            current_price = df['close'].iloc[-1]
            pos['current_price'] = current_price
            print(f"  ✅ {code} {pos['name']}: ¥{current_price:.2f}")
        else:
            # 使用腾讯财经实时价格
            import requests
            try:
                symbol = code.replace('.', '')
                url = f'http://qt.gtimg.cn/q={symbol}'
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    data = response.text
                    if '=' in data and '"' in data:
                        parts = data.split('=')[1].strip('"').split('~')
                        if len(parts) >= 4:
                            current_price = float(parts[3])
                            pos['current_price'] = current_price
                            print(f"  ✅ {code} {pos['name']}: ¥{current_price:.2f}")
            except:
                pass
    
    # 保存账户
    with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
        json.dump(account, f, ensure_ascii=False, indent=2)
    
    print("\n✅ 账户数据已更新")


def generate_combined_report():
    """生成合并报告"""
    print("="*70)
    print("  📊 生成合并报告")
    print("="*70)
    
    from datetime import datetime
    
    # 加载两个账户
    account = None
    mf_account = None
    
    if ACCOUNT_FILE.exists():
        with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
            account = json.load(f)
    
    if MF_ACCOUNT_FILE.exists():
        with open(MF_ACCOUNT_FILE, 'r', encoding='utf-8') as f:
            mf_account = json.load(f)
    
    # 生成报告
    report_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    report = f"""# 统一模拟盘系统报告

生成时间：{report_time}

## 主账户 (日线策略)
"""
    
    if account:
        total_position_value = sum(
            pos['shares'] * pos.get('current_price', pos.get('avg_price', 0))
            for pos in account.get('positions', {}).values()
        )
        total_value = account.get('cash', 0) + total_position_value
        pnl = total_value - account.get('initial_capital', 1000000)
        pnl_pct = pnl / account.get('initial_capital', 1000000) * 100
        
        report += f"""
- 初始资金：¥{account.get('initial_capital', 1000000):,.2f}
- 总资产：¥{total_value:,.2f}
- 总盈亏：¥{pnl:,.2f} ({pnl_pct:.2f}%)
- 持仓数量：{len(account.get('positions', {}))}只
"""
    else:
        report += "\n- 账户不存在\n"
    
    report += f"""
## 中频账户 (中频交易)
"""
    
    if mf_account:
        mf_pnl = mf_account.get('total_pnl', 0)
        mf_pnl_pct = mf_pnl / mf_account.get('initial_capital', 200000) * 100
        
        report += f"""
- 初始资金：¥{mf_account.get('initial_capital', 200000):,.2f}
- 总资产：¥{mf_account.get('total_value', 0):,.2f}
- 总盈亏：¥{mf_pnl:,.2f} ({mf_pnl_pct:.2f}%)
- 持仓数量：{len(mf_account.get('positions', {}))}只
"""
    else:
        report += "\n- 账户不存在\n"
    
    # 合并统计
    if account and mf_account:
        combined_initial = account.get('initial_capital', 1000000) + mf_account.get('initial_capital', 200000)
        combined_value = total_value + mf_account.get('total_value', 0)
        combined_pnl = combined_value - combined_initial
        combined_pnl_pct = combined_pnl / combined_initial * 100
        
        report += f"""
## 合并统计

- 总初始资金：¥{combined_initial:,.2f}
- 总总资产：¥{combined_value:,.2f}
- 总盈亏：¥{combined_pnl:,.2f} ({combined_pnl_pct:.2f}%)
- 总持仓数量：{len(account.get('positions', {})) + len(mf_account.get('positions', {}))}只
"""
    
    # 保存报告
    report_dir = Path('sim_trading/reports')
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = report_dir / f"combined_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(report)
    print(f"\n✅ 报告已保存：{report_file}")


def main():
    parser = argparse.ArgumentParser(description='统一模拟盘系统')
    parser.add_argument('--all', action='store_true', help='启动所有策略')
    parser.add_argument('--day', action='store_true', help='启动日线策略')
    parser.add_argument('--medium', action='store_true', help='启动中频交易')
    parser.add_argument('--status', action='store_true', help='查看系统状态')
    parser.add_argument('--sync', action='store_true', help='同步账户数据')
    parser.add_argument('--report', action='store_true', help='生成合并报告')
    
    args = parser.parse_args()
    
    if args.all:
        start_all()
    elif args.day:
        start_day_trading()
    elif args.medium:
        start_medium_frequency()
    elif args.status:
        print_status()
    elif args.sync:
        sync_accounts()
    elif args.report:
        generate_combined_report()
    else:
        # 默认显示状态
        print_status()
        print("\n使用说明:")
        print("  --all     启动所有策略")
        print("  --day     启动日线策略")
        print("  --medium  启动中频交易")
        print("  --status  查看系统状态")
        print("  --sync    同步账户数据")
        print("  --report  生成合并报告")


if __name__ == '__main__':
    main()
