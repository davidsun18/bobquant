# -*- coding: utf-8 -*-
"""
模拟实盘交易系统
初始资金 5 万，主板股票，每日记录交易和持仓
"""

import pandas as pd
import numpy as np
import baostock as bs
from datetime import datetime
import json
import os

# ==================== 配置 ====================
CONFIG = {
    'initial_capital': 50000,  # 初始资金 5 万
    'stock_pool': [
        # 银行（主板）
        ('sh.600000', '浦发银行', 'bollinger'),
        ('sh.600036', '招商银行', 'bollinger'),
        ('sh.601398', '工商银行', 'bollinger'),
        ('sh.601288', '农业银行', 'bollinger'),
        ('sh.601939', '建设银行', 'bollinger'),
        
        # 科技/制造（主板）
        ('sh.601138', '工业富联', 'macd'),
        ('sz.000001', '平安银行', 'macd'),
        ('sz.000002', '万科 A', 'bollinger'),
        
        # 消费（主板）
        ('sh.600887', '伊利股份', 'bollinger'),
        ('sz.000333', '美的集团', 'bollinger'),
        ('sh.600276', '恒瑞医药', 'macd'),
        
        # 白酒（主板）
        ('sh.600519', '贵州茅台', 'bollinger'),
        ('sh.000858', '五粮液', 'macd'),
        ('sz.000568', '泸州老窖', 'macd'),
    ],
    'max_position_per_stock': 0.2,  # 单只股票最大仓位 20%
    'stop_loss': 0.08,  # 止损 8%
    'take_profit': 0.15,  # 止盈 15%
    'output_dir': '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/'
}

# ==================== 账户管理 ====================
class TradingAccount:
    def __init__(self, account_file):
        self.account_file = account_file
        self.load_account()
    
    def load_account(self):
        """加载账户信息"""
        if os.path.exists(self.account_file):
            with open(self.account_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.cash = data['cash']
                self.positions = data['positions']  # {code: {'shares': x, 'avg_price': y}}
                self.history = data['history']  # 交易记录
                self.start_date = data['start_date']
        else:
            self.cash = CONFIG['initial_capital']
            self.positions = {}
            self.history = []
            self.start_date = datetime.now().strftime('%Y-%m-%d')
    
    def save_account(self):
        """保存账户信息"""
        data = {
            'cash': self.cash,
            'positions': self.positions,
            'history': self.history,
            'start_date': self.start_date,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        try:
            with open(self.account_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存账户失败：{e}")
    
    def get_available_cash(self):
        """获取可用资金"""
        # 计算持仓市值
        market_value = 0
        for code, pos in self.positions.items():
            if pos['shares'] > 0:
                # 获取最新价
                current_price = self.get_current_price(code)
                if current_price > 0:
                    market_value += pos['shares'] * current_price
        
        return self.cash - market_value
    
    def get_current_price(self, code):
        """获取当前价格"""
        try:
            lg = bs.login()
            rs = bs.query_history_k_data_plus(code, "date,close", 
                                               start_date='2026-03-20', end_date='2026-03-24', frequency="d")
            data = []
            while rs.next():
                data.append(rs.get_row_data())
            bs.logout()
            
            if len(data) > 0:
                return float(data[-1][1])
        except:
            pass
        return 0
    
    def buy(self, code, shares, price):
        """买入"""
        cost = shares * price
        if cost > self.cash:
            return False, "资金不足"
        
        self.cash -= cost
        
        if code not in self.positions:
            self.positions[code] = {'shares': 0, 'avg_price': 0}
        
        # 更新持仓
        old_shares = self.positions[code]['shares']
        old_avg = self.positions[code]['avg_price']
        
        new_shares = old_shares + shares
        new_avg = (old_shares * old_avg + shares * price) / new_shares if new_shares > 0 else 0
        
        self.positions[code]['shares'] = new_shares
        self.positions[code]['avg_price'] = new_avg
        
        # 记录交易
        self.history.append({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'code': code,
            'action': '买入',
            'shares': shares,
            'price': price,
            'amount': cost
        })
        
        self.save_account()
        return True, "买入成功"
    
    def sell(self, code, shares, price):
        """卖出"""
        if code not in self.positions or self.positions[code]['shares'] < shares:
            return False, "持仓不足"
        
        revenue = shares * price
        self.cash += revenue
        
        self.positions[code]['shares'] -= shares
        
        if self.positions[code]['shares'] <= 0:
            del self.positions[code]
        
        # 记录交易
        self.history.append({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'code': code,
            'action': '卖出',
            'shares': shares,
            'price': price,
            'amount': revenue
        })
        
        self.save_account()
        return True, "卖出成功"
    
    def get_portfolio_summary(self, current_prices):
        """获取投资组合汇总"""
        total_value = self.cash
        position_details = []
        
        for code, pos in self.positions.items():
            if pos['shares'] > 0:
                price = current_prices.get(code, 0)
                market_value = pos['shares'] * price
                cost_basis = pos['shares'] * pos['avg_price']
                profit_loss = market_value - cost_basis
                profit_pct = profit_loss / cost_basis * 100 if cost_basis > 0 else 0
                
                total_value += market_value
                
                position_details.append({
                    '代码': code,
                    '名称': self.get_stock_name(code),
                    '持仓': pos['shares'],
                    '成本价': pos['avg_price'],
                    '当前价': price,
                    '市值': market_value,
                    '盈亏': profit_loss,
                    '盈亏%': f"{profit_pct:.2f}%"
                })
        
        initial = CONFIG['initial_capital']
        total_return = total_value - initial
        total_return_pct = total_return / initial * 100
        
        return {
            '总资产': total_value,
            '现金': self.cash,
            '持仓市值': total_value - self.cash,
            '总盈亏': total_return,
            '总收益率': f"{total_return_pct:.2f}%",
            '持仓详情': position_details
        }
    
    def get_stock_name(self, code):
        """获取股票名称"""
        for c, name, _ in CONFIG['stock_pool']:
            if c == code:
                return name
        return code

# ==================== 交易策略 ====================
def get_trading_signal(code, strategy):
    """获取交易信号"""
    try:
        lg = bs.login()
        rs = bs.query_history_k_data_plus(code, "date,open,high,low,close,volume",
                                           start_date='2023-01-01', end_date=datetime.now().strftime('%Y-%m-%d'),
                                           frequency="d")
        data = []
        while rs.next():
            data.append(rs.get_row_data())
        bs.logout()
        
        if len(data) < 30:
            return None
        
        df = pd.DataFrame(data, columns=rs.fields)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = '观望'
        reason = ''
        
        if strategy == 'macd':
            df['ma1'] = df['close'].rolling(12).mean()
            df['ma2'] = df['close'].rolling(26).mean()
            df['volume_ma'] = df['volume'].rolling(20).mean()
            
            if (latest['ma1'] > latest['ma2'] and prev['ma1'] <= prev['ma2'] and 
                latest['volume'] > latest['volume_ma']):
                signal = '买入'
                reason = 'MACD 金叉 + 放量'
            elif latest['ma1'] < latest['ma2'] and prev['ma1'] >= prev['ma2']:
                signal = '卖出'
                reason = 'MACD 死叉'
        
        elif strategy == 'bollinger':
            df['bb_mid'] = df['close'].rolling(20).mean()
            df['bb_std'] = df['close'].rolling(20).std()
            df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
            df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
            df['bb_pos'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            if latest['bb_pos'] < 0.1:
                signal = '买入'
                reason = f'布林带下轨 (%B={latest["bb_pos"]:.2f})'
            elif latest['bb_pos'] > 0.9:
                signal = '卖出'
                reason = f'布林带上轨 (%B={latest["bb_pos"]:.2f})'
        
        return {
            'code': code,
            'signal': signal,
            'reason': reason,
            'price': latest['close'],
            'date': latest['date']
        }
    
    except Exception as e:
        return None

# ==================== 每日交易流程 ====================
def daily_trading(account):
    """每日交易流程"""
    print("="*80)
    print("📊 模拟盘每日交易")
    print("="*80)
    print(f"日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"初始资金：¥{CONFIG['initial_capital']:,.2f}")
    print("="*80)
    
    today_signals = []
    trades_executed = []
    
    # 1. 检查持仓股票
    print("\n📈 检查持仓...")
    for code in list(account.positions.keys()):
        for c, name, strategy in CONFIG['stock_pool']:
            if c == code:
                signal = get_trading_signal(code, strategy)
                if signal and signal['signal'] == '卖出':
                    # 卖出
                    current_price = account.get_current_price(code)
                    shares = account.positions[code]['shares']
                    success, msg = account.sell(code, shares, current_price)
                    
                    trades_executed.append({
                        '股票': f"{code} {name}",
                        '操作': '卖出',
                        '数量': shares,
                        '价格': current_price,
                        '金额': shares * current_price,
                        '原因': signal['reason']
                    })
                    print(f"  🔴 卖出 {name}: {shares}股 @ ¥{current_price:.2f}")
                break
    
    # 2. 扫描股票池寻找买入机会
    print("\n🔍 扫描买入机会...")
    available_cash = account.cash
    
    for code, name, strategy in CONFIG['stock_pool']:
        # 跳过已持仓
        if code in account.positions:
            continue
        
        signal = get_trading_signal(code, strategy)
        if signal and signal['signal'] == '买入':
            today_signals.append({
                'code': code,
                'name': name,
                'strategy': strategy,
                'signal': signal['signal'],
                'reason': signal['reason'],
                'price': signal['price']
            })
            
            # 计算买入数量（20% 仓位）
            max_amount = CONFIG['initial_capital'] * CONFIG['max_position_per_stock']
            shares = int(max_amount / signal['price'] / 100) * 100  # 100 股整数倍
            
            if shares > 0 and shares * signal['price'] <= available_cash:
                # 执行买入
                success, msg = account.buy(code, shares, signal['price'])
                if success:
                    cost = shares * signal['price']
                    available_cash -= cost
                    
                    trades_executed.append({
                        '股票': f"{code} {name}",
                        '操作': '买入',
                        '数量': shares,
                        '价格': signal['price'],
                        '金额': cost,
                        '原因': signal['reason']
                    })
                    print(f"  🟢 买入 {name}: {shares}股 @ ¥{signal['price']:.2f} (花费 ¥{cost:,.2f})")
    
    # 3. 生成报告
    print("\n" + "="*80)
    print("📊 今日交易汇总")
    print("="*80)
    
    if len(trades_executed) == 0:
        print("  今日无交易")
    else:
        for trade in trades_executed:
            emoji = '🟢' if trade['操作'] == '买入' else '🔴'
            print(f"  {emoji} {trade['股票']}: {trade['操作']} {trade['数量']}股 @ ¥{trade['价格']:.2f} = ¥{trade['金额']:,.2f}")
            print(f"     原因：{trade['原因']}")
    
    # 4. 账户汇总
    print("\n" + "="*80)
    print("📊 账户汇总")
    print("="*80)
    
    # 获取当前价格
    current_prices = {}
    for code in account.positions.keys():
        current_prices[code] = account.get_current_price(code)
    
    summary = account.get_portfolio_summary(current_prices)
    
    print(f"  现金：¥{summary['现金']:,.2f}")
    print(f"  持仓市值：¥{summary['持仓市值']:,.2f}")
    print(f"  总资产：¥{summary['总资产']:,.2f}")
    print(f"  总盈亏：¥{summary['总盈亏']:,.2f} ({summary['总收益率']})")
    
    if len(summary['持仓详情']) > 0:
        print(f"\n📈 持仓明细:")
        for pos in summary['持仓详情']:
            profit_emoji = '🟢' if pos['盈亏'] > 0 else '🔴' if pos['盈亏'] < 0 else '⚪'
            print(f"  {profit_emoji} {pos['代码']} {pos['名称']}: {pos['持仓']}股 "
                  f"成本¥{pos['成本价']:.2f} 现价¥{pos['当前价']:.2f} "
                  f"盈亏¥{pos['盈亏']:,.2f} ({pos['盈亏%']})")
    
    # 5. 保存报告
    os.makedirs(CONFIG['output_dir'], exist_ok=True)
    date_str = datetime.now().strftime('%Y%m%d')
    
    # 保存 CSV
    if len(trades_executed) > 0:
        df_trades = pd.DataFrame(trades_executed)
        df_trades.to_csv(f"{CONFIG['output_dir']}trades_{date_str}.csv", index=False, encoding='utf-8-sig')
    
    # 保存汇总
    report = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'trades': trades_executed,
        'signals': today_signals,
        'summary': summary
    }
    
    with open(f"{CONFIG['output_dir']}report_{date_str}.json", 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 报告已保存：{CONFIG['output_dir']}")
    
    return report

# ==================== 主函数 ====================
if __name__ == '__main__':
    os.makedirs(CONFIG['output_dir'], exist_ok=True)
    
    account_file = f"{CONFIG['output_dir']}account.json"
    account = TradingAccount(account_file)
    
    print("="*80)
    print("🎯 模拟实盘交易系统")
    print("="*80)
    print(f"初始资金：¥{CONFIG['initial_capital']:,.2f}")
    print(f"股票池：{len(CONFIG['stock_pool'])} 只主板股票")
    print(f"单只最大仓位：{CONFIG['max_position_per_stock']*100}%")
    print(f"止损：{CONFIG['stop_loss']*100}% | 止盈：{CONFIG['take_profit']*100}%")
    print("="*80)
    
    report = daily_trading(account)
    
    print("\n" + "="*80)
    print("📚 使用说明")
    print("="*80)
    print("""
✅ 每日运行:
  python3 sim_trading_system.py

📊 查看报告:
  - 交易记录：sim_trading/trades_YYYYMMDD.csv
  - 每日报告：sim_trading/report_YYYYMMDD.json
  - 账户状态：sim_trading/account.json

📈 重置账户:
  删除 sim_trading/account.json 即可重新开始

⚠️ 风险提示:
  本系统为模拟盘，不构成真实投资建议
  实盘需谨慎，注意风险控制
    """)
