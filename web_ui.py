# -*- coding: utf-8 -*-
"""
BOB 量化系统 - Web UI 界面
实时显示持仓、盈亏、资产等信息，每 5 秒刷新
"""

from flask import Flask, render_template, jsonify, request
import json
import os
import requests
from datetime import datetime

app = Flask(__name__)

# 配置
ACCOUNT_FILE = '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/account_ideal.json'
TRADE_LOG_FILE = '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/交易记录.json'

# 股票代码转中文名称映射
STOCK_NAMES = {
    'sh.601398': '工商银行',
    'sh.601288': '农业银行',
    'sh.601939': '建设银行',
    'sh.600036': '招商银行',
    'sh.601166': '兴业银行',
    'sh.600016': '民生银行',
    'sh.601988': '中国银行',
    'sh.601328': '交通银行',
    'sh.601658': '邮储银行',
    'sz.000001': '平安银行',
    'sh.600519': '贵州茅台',
    'sh.000858': '五粮液',
    'sz.000568': '泸州老窖',
    'sh.600809': '山西汾酒',
    'sh.600702': '舍得酒业',
    'sh.600779': '水井坊',
    'sh.603198': '迎驾贡酒',
    'sh.603369': '今世缘',
    'sh.601138': '工业富联',
    'sh.688981': '中芯国际',
    'sz.002371': '北方华创',
    'sz.002156': '通富微电',
    'sz.002185': '华天科技',
    'sz.002049': '紫光国微',
    'sz.002415': '海康威视',
    'sh.600584': '长电科技',
    'sh.603501': '韦尔股份',
    'sh.603986': '兆易创新',
    'sz.002594': '比亚迪',
    'sz.300750': '宁德时代',
    'sz.002460': '赣锋锂业',
    'sz.002466': '天齐锂业',
    'sz.002709': '天赐材料',
    'sz.002812': '恩捷股份',
    'sh.601012': '隆基绿能',
    'sh.600438': '通威股份',
    'sh.600276': '恒瑞医药',
    'sh.600085': '同仁堂',
    'sh.600436': '片仔癀',
    'sh.603259': '药明康德',
    'sz.000538': '云南白药',
    'sz.000661': '长春高新',
    'sz.000333': '美的集团',
    'sz.000651': '格力电器',
    'sh.600887': '伊利股份',
    'sh.600690': '海尔智家',
    'sh.601888': '中国中免',
    'sh.600028': '中国石化',
    'sh.600309': '万华化学',
    'sh.600547': '山东黄金',
}

def get_stock_name(code):
    """获取股票中文名称"""
    if code in STOCK_NAMES:
        return STOCK_NAMES[code]
    return code

def get_realtime_price(code):
    """获取实时价格（腾讯财经）"""
    try:
        symbol = code.replace('.', '')
        url = f'http://qt.gtimg.cn/q={symbol}'
        response = requests.get(url, timeout=2)
        
        if response.status_code == 200:
            data = response.text
            if '=' in data and '"' in data:
                parts = data.split('=')[1].strip('"').split('~')
                if len(parts) >= 4:
                    return float(parts[3])
    except:
        pass
    return None

def load_account():
    """加载账户数据"""
    if os.path.exists(ACCOUNT_FILE):
        with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def load_trades():
    """加载交易记录"""
    if os.path.exists(TRADE_LOG_FILE):
        with open(TRADE_LOG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'history' in data:
                return data['history']
    return []

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/account')
def api_account():
    """账户数据 API"""
    account = load_account()
    if not account:
        return jsonify({'error': '账户数据不存在'})
    
    # 计算总资产
    initial = account.get('initial_capital', 1000000)
    cash = account.get('cash', 0)
    positions = account.get('positions', {})
    
    # 获取今天的日期
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 计算持仓市值和盈亏
    market_value = 0
    total_profit = 0
    position_list = []
    
    for code, pos in positions.items():
        shares = pos.get('shares', 0)
        avg_price = pos.get('avg_price', 0)
        cost = shares * avg_price
        
        # 获取中文名称
        name = get_stock_name(code)
        
        # 获取实时价格
        current_price = get_realtime_price(code)
        if current_price is None:
            current_price = avg_price  # 如果获取失败，用成本价
        
        mv = shares * current_price
        profit = mv - cost
        profit_pct = (profit / cost * 100) if cost > 0 else 0
        
        # T+1 规则：计算今天买入的总股数（不可卖）
        # 直接从持仓的 buy_lots 计算，避免交易记录重复统计的问题
        today_bought = 0
        buy_lots = pos.get('buy_lots', [])
        for lot in buy_lots:
            if lot.get('date', '') == today:
                today_bought += lot.get('shares', 0)
        # 如果没有 buy_lots 或今天买入为 0，用 buy_date 兜底
        if today_bought == 0:
            buy_date = pos.get('buy_date', '')
            if buy_date == today:
                today_bought = shares
        
        market_value += mv
        total_profit += profit
        
        position_list.append({
            'code': code,
            'name': name,
            'shares': shares,
            'avg_price': avg_price,
            'current_price': current_price,
            'cost': cost,
            'market_value': mv,
            'profit': profit,
            'profit_pct': profit_pct,
            'today_bought': today_bought  # 今天买入的数量（不可卖）
        })
    
    total_assets = cash + market_value
    profit_today = total_assets - initial
    
    return jsonify({
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'initial_capital': initial,
        'cash': cash,
        'market_value': market_value,
        'total_assets': total_assets,
        'total_profit': total_profit,
        'profit_today': profit_today,
        'positions': position_list
    })

@app.route('/api/trades')
def api_trades():
    """交易记录 API"""
    trades = load_trades()
    
    # 如果交易记录为空，检查账户文件中的 history
    if not trades:
        account = load_account()
        if account and 'trade_history' in account:
            trades = account['trade_history']
    
    return jsonify({'trades': trades})  # 返回全部记录

@app.route('/api/stock/<code>')
def api_stock_detail(code):
    """单个股票详情 API"""
    account = load_account()
    if not account:
        return jsonify({'error': '账户数据不存在'})
    
    positions = account.get('positions', {})
    
    if code not in positions:
        return jsonify({'error': '未找到该股票持仓'})
    
    pos = positions[code]
    shares = pos.get('shares', 0)
    avg_price = pos.get('avg_price', 0)
    cost = shares * avg_price
    
    # 获取实时价格
    current_price = get_realtime_price(code)
    if current_price is None:
        current_price = avg_price
    
    mv = shares * current_price
    profit = mv - cost
    profit_pct = (profit / cost * 100) if cost > 0 else 0
    
    # 获取该股票的交易记录
    all_trades = load_trades()
    stock_trades = [t for t in all_trades if t.get('code') == code]
    
    return jsonify({
        'code': code,
        'name': get_stock_name(code),
        'shares': shares,
        'avg_price': avg_price,
        'current_price': current_price,
        'cost': cost,
        'market_value': mv,
        'profit': profit,
        'profit_pct': profit_pct,
        'trades': stock_trades[-10:]  # 返回最近 10 条
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
