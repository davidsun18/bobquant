# -*- coding: utf-8 -*-
"""
BobQuant 交互式可视化 Dashboard
基于 Plotly Dash 实现

功能：
- K 线蜡烛图（交互式）
- 成交量柱状图
- 技术指标叠加（MA/MACD/布林带）
- 持仓盈亏饼图
- 交易记录表格
- 实时刷新（3 秒）

访问地址：http://localhost:8050
"""

import sys
import os
import json
from datetime import datetime, timedelta

# 添加路径以导入 bobquant 模块
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, callback, ctx
import dash_bootstrap_components as dbc

# 导入数据源
from bobquant.data.provider import get_provider
from bobquant.core.account import get_sellable_shares

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
                trades = data
            elif isinstance(data, dict) and 'history' in data:
                trades = data['history']
            else:
                return []
            
            finalized_trades = []
            for t in trades:
                trade_id = t.get('trade_id', '')
                status = t.get('status', '')
                if trade_id and status == 'completed':
                    finalized_trades.append(t)
            
            return finalized_trades
    return []

def get_historical_data(code, days=60):
    """获取历史 K 线数据"""
    provider = get_provider('tencent')
    df = provider.get_history(code, days=days)
    if df is not None:
        # 计算技术指标
        df = calculate_indicators(df)
    return df

def calculate_indicators(df):
    """计算技术指标：MA, MACD, 布林带"""
    if df is None or len(df) < 30:
        return df
    
    # MA5, MA10, MA20
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA10'] = df['close'].rolling(window=10).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal']
    
    # 布林带
    df['BB_Middle'] = df['close'].rolling(window=20).mean()
    std = df['close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (std * 2)
    
    return df

def create_candlestick_chart(code, df):
    """创建 K 线蜡烛图（含成交量和技术指标）"""
    if df is None or len(df) == 0:
        return go.Figure().add_annotation(text="暂无数据", showarrow=False)
    
    # 创建子图：K 线 + 成交量 + MACD
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.5, 0.2, 0.15, 0.15],
        subplot_titles=(f'{code} K 线图', '成交量', 'MACD', '布林带')
    )
    
    # K 线蜡烛图
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='K 线',
            increasing_line_color='#ff4d4f',
            decreasing_line_color='#52c41a',
            increasing_fillcolor='#ff4d4f',
            decreasing_fillcolor='#52c41a',
        ),
        row=1, col=1
    )
    
    # MA 均线
    fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='#ffa500', width=1), name='MA5'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], line=dict(color='#00bfff', width=1), name='MA10'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#9370db', width=1), name='MA20'), row=1, col=1)
    
    # 布林带
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], line=dict(color='#ff69b4', width=1, dash='dash'), name='BB 上轨'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], line=dict(color='#ff69b4', width=1, dash='dash'), name='BB 下轨'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Middle'], line=dict(color='#ff69b4', width=1), name='BB 中轨', fill='none'), row=1, col=1)
    
    # 成交量柱状图
    colors = ['#ff4d4f' if df['close'].iloc[i] >= df['open'].iloc[i] else '#52c41a' for i in range(len(df))]
    fig.add_trace(
        go.Bar(x=df.index, y=df['volume'], name='成交量', marker_color=colors, opacity=0.7),
        row=2, col=1
    )
    
    # MACD
    fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='MACD 柱', marker_color=['#ff4d4f' if v > 0 else '#52c41a' for v in df['MACD_Hist']], opacity=0.7), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#ffa500', width=1), name='MACD'), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], line=dict(color='#00bfff', width=1), name='Signal'), row=3, col=1)
    
    # 布林带宽度（单独显示）
    bb_width = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle'] * 100
    fig.add_trace(go.Scatter(x=df.index, y=bb_width, line=dict(color='#9370db', width=1), name='BB 宽度%', fill='tozeroy'), row=4, col=1)
    
    # 更新布局
    fig.update_layout(
        height=800,
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode='x unified',
        template='plotly_white',
        margin=dict(l=50, r=50, t=50, b=50),
    )
    
    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    fig.update_yaxes(title_text="BB 宽度%", row=4, col=1)
    
    return fig

def create_pie_chart(positions):
    """创建持仓盈亏饼图"""
    if not positions or len(positions) == 0:
        return go.Figure().add_annotation(text="暂无持仓", showarrow=False)
    
    # 准备数据
    labels = []
    values = []
    colors = []
    
    for pos in positions:
        name = pos.get('name', pos.get('code', 'Unknown'))
        profit = pos.get('profit', 0)
        labels.append(name)
        values.append(abs(profit))
        colors.append('#ff4d4f' if profit >= 0 else '#52c41a')
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker_colors=colors,
        textinfo='label+percent',
        hovertemplate='%{label}<br>盈亏：¥%{value:,.2f}<extra></extra>'
    )])
    
    fig.update_layout(
        height=400,
        title_text='持仓盈亏分布',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template='plotly_white',
        margin=dict(l=20, r=20, t=50, b=20),
    )
    
    return fig

def create_trades_table(trades):
    """创建交易记录表格"""
    if not trades or len(trades) == 0:
        return html.Div("暂无交易记录", style={'textAlign': 'center', 'padding': '40px', 'color': '#999'})
    
    # 限制显示最近 50 条
    recent_trades = trades[-50:][::-1]
    
    rows = []
    for trade in recent_trades:
        is_buy = '买入' in trade.get('action', '') or '加仓' in trade.get('action', '')
        action_color = '#ff4d4f' if is_buy else '#52c41a'
        amount = trade.get('shares', 0) * trade.get('price', 0)
        
        row = html.Tr([
            html.Td(trade.get('time', '')[:16], style={'fontSize': '12px', 'color': '#666'}),
            html.Td(trade.get('name', ''), style={'fontWeight': '500'}),
            html.Td(trade.get('action', ''), style={'color': action_color, 'fontWeight': '600'}),
            html.Td(str(trade.get('shares', 0))),
            html.Td(f"¥{trade.get('price', 0):.2f}"),
            html.Td(f"¥{amount:,.2f}", style={'fontWeight': '600', 'color': '#667eea'}),
        ])
        rows.append(row)
    
    table = html.Table([
        html.Thead([
            html.Tr([
                html.Th('时间', style={'textAlign': 'left'}),
                html.Th('股票'),
                html.Th('操作'),
                html.Th('数量'),
                html.Th('价格'),
                html.Th('金额'),
            ])
        ]),
        html.Tbody(rows)
    ], style={'width': '100%', 'borderCollapse': 'collapse'})
    
    return html.Div(table, style={'overflowX': 'auto'})

def create_dashboard_layout():
    """创建 Dashboard 主布局"""
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H1("🚀 BobQuant 交互式 Dashboard", style={'color': '#667eea', 'marginBottom': '10px'}),
                html.Div(id='last-update', style={'color': '#666', 'fontSize': '14px'}),
            ], width=12)
        ], className="mb-4"),
        
        # 资产概览卡片
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("💰 总资产", className="card-title text-muted"),
                        html.H3(id='total-assets', className="card-text"),
                    ])
                ], color="primary", outline=True)
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("📈 证券市值", className="card-title text-muted"),
                        html.H3(id='market-value', className="card-text"),
                    ])
                ], color="info", outline=True)
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("💵 可用现金", className="card-title text-muted"),
                        html.H3(id='cash', className="card-text"),
                    ])
                ], color="success", outline=True)
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("📊 持仓盈亏", className="card-title text-muted"),
                        html.H3(id='position-profit', className="card-text"),
                    ])
                ], color="danger", outline=True)
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("📉 当日盈亏", className="card-title text-muted"),
                        html.H3(id='today-profit', className="card-text"),
                    ])
                ], color="warning", outline=True)
            ], width=2),
        ], className="mb-4"),
        
        # K 线图 + 持仓饼图
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("📊 K 线与技术指标", className="mb-0"),
                        dcc.Dropdown(
                            id='stock-selector',
                            options=[],
                            value=None,
                            placeholder='选择股票...',
                            style={'width': '200px', 'float': 'right', 'marginTop': '-35px'}
                        ),
                    ]),
                    dbc.CardBody([
                        dcc.Graph(id='candlestick-chart', config={'displayModeBar': True, 'scrollZoom': True}),
                    ])
                ])
            ], width=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("📈 持仓盈亏分布", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(id='pie-chart', config={'displayModeBar': False}),
                    ])
                ])
            ], width=4),
        ], className="mb-4"),
        
        # 交易记录表格
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("📝 交易记录", className="mb-0")),
                    dbc.CardBody([
                        html.Div(id='trades-table'),
                    ])
                ])
            ], width=12),
        ], className="mb-4"),
        
        # 自动刷新
        dcc.Interval(id='interval-component', interval=3*1000, n_intervals=0),
        
    ], fluid=True, style={'paddingTop': '20px', 'paddingBottom': '20px'})

# 创建 Dash 应用
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "BobQuant Dashboard"
app.layout = create_dashboard_layout()

@callback(
    [Output('stock-selector', 'options'),
     Output('stock-selector', 'value'),
     Output('total-assets', 'children'),
     Output('market-value', 'children'),
     Output('cash', 'children'),
     Output('position-profit', 'children'),
     Output('today-profit', 'children'),
     Output('candlestick-chart', 'figure'),
     Output('pie-chart', 'figure'),
     Output('trades-table', 'children'),
     Output('last-update', 'children')],
    [Input('interval-component', 'n_intervals'),
     Input('stock-selector', 'value')]
)
def update_dashboard(n_intervals, selected_stock):
    """更新 Dashboard 数据"""
    # 加载账户数据
    account = load_account()
    trades = load_trades()
    
    # 默认值
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    default_fig = go.Figure().add_annotation(text="加载中...", showarrow=False)
    default_pie = go.Figure().add_annotation(text="加载中...", showarrow=False)
    default_table = html.Div("加载中...", style={'textAlign': 'center', 'padding': '40px'})
    
    if not account:
        return [], None, "--", "--", "--", "--", "--", default_fig, default_pie, default_table, f"最后更新：{now} (无账户数据)"
    
    # 计算资产数据
    initial = account.get('initial_capital', 1000000)
    cash = account.get('cash', 0)
    positions = account.get('positions', {})
    
    market_value = 0
    total_profit = 0
    position_list = []
    today_profit = 0
    
    for code, pos in positions.items():
        shares = pos.get('shares', 0)
        avg_price = pos.get('avg_price', 0)
        cost = shares * avg_price
        
        name = get_stock_name(code)
        
        # 获取实时价格
        from bobquant.data.provider import get_provider
        provider = get_provider('tencent')
        quote = provider.get_quote(code)
        
        if quote:
            current_price = quote['current']
            pre_close = quote['pre_close']
        else:
            current_price = avg_price
            pre_close = avg_price
        
        mv = shares * current_price
        profit = mv - cost
        profit_pct = (profit / cost * 100) if cost > 0 else 0
        today_profit += (current_price - pre_close) * shares
        
        market_value += mv
        total_profit += profit
        
        sellable = get_sellable_shares(pos)
        
        position_list.append({
            'code': code,
            'name': name,
            'shares': shares,
            'avg_price': avg_price,
            'current_price': current_price,
            'profit': profit,
            'profit_pct': profit_pct,
            'sellable': sellable,
        })
    
    total_assets = cash + market_value
    
    # 股票选择器选项
    stock_options = [{'label': f"{p['name']} ({p['code']})", 'value': p['code']} for p in position_list]
    selected_stock = selected_stock if selected_stock and selected_stock in [opt['value'] for opt in stock_options] else (stock_options[0]['value'] if stock_options else None)
    
    # K 线图
    if selected_stock:
        df = get_historical_data(selected_stock, days=60)
        candlestick_fig = create_candlestick_chart(selected_stock, df)
    else:
        candlestick_fig = default_fig
    
    # 持仓饼图
    pie_fig = create_pie_chart(position_list)
    
    # 交易记录表格
    trades_table = create_trades_table(trades)
    
    # 格式化数字
    def fmt(val):
        return f"¥{val:,.2f}" if isinstance(val, (int, float)) else str(val)
    
    def fmt_profit(val):
        prefix = '+' if val >= 0 else ''
        color = 'success' if val >= 0 else 'danger'
        return html.Span(f"{prefix}¥{abs(val):,.2f}", style={'color': '#52c41a' if val >= 0 else '#ff4d4f'})
    
    return (
        stock_options,
        selected_stock,
        fmt(total_assets),
        fmt(market_value),
        fmt(cash),
        fmt_profit(total_profit),
        fmt_profit(today_profit),
        candlestick_fig,
        pie_fig,
        trades_table,
        f"最后更新：{now} (每 3 秒自动刷新)"
    )

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 BobQuant Dashboard 启动中...")
    print("=" * 60)
    print("📊 访问地址：http://localhost:8050")
    print("📊 局域网访问：http://<本机 IP>:8050")
    print("=" * 60)
    print("功能列表:")
    print("  ✅ K 线蜡烛图（交互式）")
    print("  ✅ 成交量柱状图")
    print("  ✅ 技术指标叠加（MA/MACD/布林带）")
    print("  ✅ 持仓盈亏饼图")
    print("  ✅ 交易记录表格")
    print("  ✅ 实时刷新（3 秒）")
    print("=" * 60)
    
    # 启动服务器
    app.run(host='0.0.0.0', port=8050, debug=False)
