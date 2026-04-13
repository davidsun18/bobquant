# -*- coding: utf-8 -*-
"""
BobQuant Streamlit 可视化看板

功能：
- 账户概览
- 持仓分析
- 交易记录
- 绩效图表
- 实时刷新
- 多页面导航

访问地址：http://localhost:8501
"""

import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# 添加路径以导入 bobquant 模块
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 配置
ACCOUNT_FILE = '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/account_ideal.json'
TRADE_LOG_FILE = '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/交易记录.json'
LOG_FILE = '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/模拟盘日志.log'

# 股票代码转中文名称映射
STOCK_NAMES = {
    'sh.601398': '工商银行', 'sh.601288': '农业银行', 'sh.601939': '建设银行',
    'sh.600036': '招商银行', 'sh.601166': '兴业银行', 'sh.600016': '民生银行',
    'sh.601988': '中国银行', 'sh.601328': '交通银行', 'sh.601658': '邮储银行',
    'sz.000001': '平安银行', 'sh.600519': '贵州茅台', 'sh.000858': '五粮液',
    'sz.000568': '泸州老窖', 'sh.600809': '山西汾酒', 'sh.600702': '舍得酒业',
    'sh.600779': '水井坊', 'sh.603198': '迎驾贡酒', 'sh.603369': '今世缘',
    'sh.601138': '工业富联', 'sh.688981': '中芯国际', 'sz.002371': '北方华创',
    'sz.002156': '通富微电', 'sz.002185': '华天科技', 'sz.002049': '紫光国微',
    'sz.002415': '海康威视', 'sh.600584': '长电科技', 'sh.603501': '韦尔股份',
    'sh.603986': '兆易创新', 'sz.002594': '比亚迪', 'sz.300750': '宁德时代',
    'sz.002460': '赣锋锂业', 'sz.002466': '天齐锂业', 'sz.002709': '天赐材料',
    'sz.002812': '恩捷股份', 'sh.601012': '隆基绿能', 'sh.600438': '通威股份',
    'sh.600276': '恒瑞医药', 'sh.600085': '同仁堂', 'sh.600436': '片仔癀',
    'sh.603259': '药明康德', 'sz.000538': '云南白药', 'sz.000661': '长春高新',
    'sz.000333': '美的集团', 'sz.000651': '格力电器', 'sh.600887': '伊利股份',
    'sh.600690': '海尔智家', 'sh.601888': '中国中免', 'sh.600028': '中国石化',
    'sh.600309': '万华化学', 'sh.600547': '山东黄金',
}

def get_stock_name(code):
    """获取股票中文名称"""
    if code in STOCK_NAMES:
        return STOCK_NAMES[code]
    return code

@st.cache_data(ttl=30)
def load_account():
    """加载账户数据"""
    if os.path.exists(ACCOUNT_FILE):
        with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

@st.cache_data(ttl=30)
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
    try:
        from bobquant.data.provider import get_provider
        provider = get_provider('tencent')
        df = provider.get_history(code, days=days)
        if df is not None:
            df = calculate_indicators(df)
        return df
    except Exception as e:
        st.error(f"获取数据失败：{str(e)}")
        return None

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
        fig = go.Figure()
        fig.add_annotation(text="暂无数据", showarrow=False, font_size=20)
        return fig
    
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
    
    # 布林带
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], line=dict(color='#ff69b4', width=1, dash='dash'), name='BB 上轨'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], line=dict(color='#ff69b4', width=1, dash='dash'), name='BB 下轨'), row=1, col=1)
    
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
    
    return fig

def create_performance_chart(account, trades):
    """创建绩效图表"""
    if not account or not trades:
        fig = go.Figure()
        fig.add_annotation(text="暂无数据", showarrow=False, font_size=20)
        return fig
    
    # 计算累计收益
    initial = account.get('initial_capital', 1000000)
    current_positions = account.get('positions', {})
    
    # 从交易记录计算资金曲线
    trade_dates = []
    cumulative_values = []
    cumulative = initial
    
    for trade in trades:
        trade_date = trade.get('time', '')[:10]
        amount = trade.get('shares', 0) * trade.get('price', 0)
        
        if '买入' in trade.get('action', '') or '加仓' in trade.get('action', ''):
            cumulative -= amount
        else:
            cumulative += amount
        
        trade_dates.append(trade_date)
        cumulative_values.append(cumulative)
    
    # 添加当前值
    current_value = account.get('cash', 0)
    for code, pos in current_positions.items():
        current_value += pos.get('shares', 0) * pos.get('current_price', pos.get('avg_price', 0))
    
    trade_dates.append(datetime.now().strftime('%Y-%m-%d'))
    cumulative_values.append(current_value)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trade_dates,
        y=cumulative_values,
        mode='lines+markers',
        name='资金曲线',
        line=dict(color='#667eea', width=2),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.1)'
    ))
    
    fig.update_layout(
        title='资金曲线',
        xaxis_title='日期',
        yaxis_title='资产总额 (¥)',
        hovermode='x unified',
        template='plotly_white',
        height=400,
        margin=dict(l=50, r=50, t=50, b=50),
    )
    
    return fig

def create_position_pie_chart(positions):
    """创建持仓占比饼图"""
    if not positions or len(positions) == 0:
        fig = go.Figure()
        fig.add_annotation(text="暂无持仓", showarrow=False, font_size=20)
        return fig
    
    labels = []
    values = []
    colors = []
    
    for pos in positions:
        name = pos.get('name', pos.get('code', 'Unknown'))
        mv = pos.get('shares', 0) * pos.get('current_price', pos.get('avg_price', 0))
        labels.append(name)
        values.append(mv)
        colors.append(plt_color(len(labels)))
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker_colors=colors,
        textinfo='label+percent',
        hovertemplate='%{label}<br>市值：¥%{value:,.2f}<extra></extra>'
    )])
    
    fig.update_layout(
        height=400,
        title_text='持仓市值分布',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template='plotly_white',
        margin=dict(l=20, r=20, t=50, b=20),
    )
    
    return fig

def plt_color(idx):
    """生成颜色"""
    colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#fee140', '#30cfd0', '#a8edea']
    return colors[idx % len(colors)]

def get_realtime_quotes(code):
    """获取实时报价"""
    try:
        from bobquant.data.provider import get_provider
        provider = get_provider('tencent')
        return provider.get_quote(code)
    except:
        return None

# ==================== 页面定义 ====================

def page_overview():
    """账户概览页面"""
    st.title("📊 账户概览")
    
    # 加载数据
    account = load_account()
    trades = load_trades()
    
    if not account:
        st.error("未找到账户数据，请确保模拟盘已启动")
        return
    
    # 计算资产数据
    initial = account.get('initial_capital', 1000000)
    cash = account.get('cash', 0)
    positions = account.get('positions', {})
    
    market_value = 0
    total_profit = 0
    position_list = []
    
    for code, pos in positions.items():
        shares = pos.get('shares', 0)
        avg_price = pos.get('avg_price', 0)
        cost = shares * avg_price
        name = pos.get('name', get_stock_name(code))
        
        # 获取实时价格
        quote = get_realtime_quotes(code)
        if quote:
            current_price = quote['current']
            pre_close = quote['pre_close']
        else:
            current_price = pos.get('current_price', avg_price)
            pre_close = avg_price
        
        mv = shares * current_price
        profit = mv - cost
        profit_pct = (profit / cost * 100) if cost > 0 else 0
        
        market_value += mv
        total_profit += profit
        
        position_list.append({
            'code': code,
            'name': name,
            'shares': shares,
            'avg_price': avg_price,
            'current_price': current_price,
            'market_value': mv,
            'profit': profit,
            'profit_pct': profit_pct,
        })
    
    total_assets = cash + market_value
    total_return = total_assets - initial
    total_return_pct = (total_return / initial * 100) if initial > 0 else 0
    
    # 关键指标卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="💰 总资产",
            value=f"¥{total_assets:,.2f}",
            delta=f"{total_return_pct:.2f}%"
        )
    
    with col2:
        st.metric(
            label="📈 证券市值",
            value=f"¥{market_value:,.2f}",
            delta=f"¥{total_profit:,.2f}"
        )
    
    with col3:
        st.metric(
            label="💵 可用现金",
            value=f"¥{cash:,.2f}",
            delta=None
        )
    
    with col4:
        st.metric(
            label="📊 持仓盈亏",
            value=f"¥{total_profit:,.2f}",
            delta=f"{total_profit/initial*100:.2f}%" if initial > 0 else None
        )
    
    # 资金曲线
    st.subheader("📈 资金曲线")
    perf_chart = create_performance_chart(account, trades)
    st.plotly_chart(perf_chart, use_container_width=True)
    
    # 持仓明细
    st.subheader("📋 持仓明细")
    if position_list:
        df = pd.DataFrame(position_list)
        df = df[['code', 'name', 'shares', 'avg_price', 'current_price', 'market_value', 'profit', 'profit_pct']]
        df.columns = ['代码', '名称', '股数', '均价', '现价', '市值', '盈亏', '盈亏%']
        
        # 格式化
        df['盈亏'] = df['盈亏'].apply(lambda x: f"¥{x:,.2f}")
        df['盈亏%'] = df['盈亏%'].apply(lambda x: f"{x:.2f}%")
        df['市值'] = df['市值'].apply(lambda x: f"¥{x:,.2f}")
        
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无持仓")
    
    # 自动刷新按钮
    if st.button("🔄 刷新数据"):
        st.cache_data.clear()
        st.rerun()

def page_positions():
    """持仓分析页面"""
    st.title("📈 持仓分析")
    
    account = load_account()
    
    if not account:
        st.error("未找到账户数据")
        return
    
    positions = account.get('positions', {})
    
    if not positions:
        st.info("暂无持仓")
        return
    
    # 构建持仓列表
    position_list = []
    for code, pos in positions.items():
        shares = pos.get('shares', 0)
        avg_price = pos.get('avg_price', 0)
        name = pos.get('name', get_stock_name(code))
        
        quote = get_realtime_quotes(code)
        if quote:
            current_price = quote['current']
            pre_close = quote['pre_close']
        else:
            current_price = pos.get('current_price', avg_price)
            pre_close = avg_price
        
        mv = shares * current_price
        cost = shares * avg_price
        profit = mv - cost
        profit_pct = (profit / cost * 100) if cost > 0 else 0
        today_profit = (current_price - pre_close) * shares
        
        position_list.append({
            'code': code,
            'name': name,
            'shares': shares,
            'avg_price': avg_price,
            'current_price': current_price,
            'market_value': mv,
            'cost': cost,
            'profit': profit,
            'profit_pct': profit_pct,
            'today_profit': today_profit,
        })
    
    # 持仓占比饼图
    col1, col2 = st.columns(2)
    with col1:
        pie_chart = create_position_pie_chart(position_list)
        st.plotly_chart(pie_chart, use_container_width=True)
    
    with col2:
        # 盈亏分布
        profits = [p['profit'] for p in position_list]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[p['name'] for p in position_list],
            y=profits,
            marker_color=['#ff4d4f' if v >= 0 else '#52c41a' for v in profits],
            text=[f"¥{v:,.2f}" for v in profits],
            textposition='auto',
        ))
        fig.update_layout(
            title='个股盈亏分布',
            xaxis_title='股票',
            yaxis_title='盈亏 (¥)',
            template='plotly_white',
            height=400,
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 持仓明细表格
    st.subheader("📋 持仓详情")
    df = pd.DataFrame(position_list)
    df = df.sort_values('market_value', ascending=False)
    
    # 格式化显示
    display_df = df[['name', 'code', 'shares', 'avg_price', 'current_price', 'market_value', 'profit', 'profit_pct', 'today_profit']].copy()
    display_df.columns = ['名称', '代码', '股数', '成本价', '现价', '市值', '总盈亏', '盈亏%', '今日盈亏']
    display_df['市值'] = display_df['市值'].apply(lambda x: f"¥{x:,.2f}")
    display_df['总盈亏'] = display_df['总盈亏'].apply(lambda x: f"¥{x:,.2f}")
    display_df['盈亏%'] = display_df['盈亏%'].apply(lambda x: f"{x:.2f}%")
    display_df['今日盈亏'] = display_df['今日盈亏'].apply(lambda x: f"¥{x:,.2f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # K 线图选择
    st.subheader("📊 K 线图")
    stock_options = {p['code']: f"{p['name']} ({p['code']})" for p in position_list}
    selected_code = st.selectbox("选择股票", options=list(stock_options.keys()), format_func=lambda x: stock_options[x])
    
    if selected_code:
        df_data = get_historical_data(selected_code, days=60)
        if df_data is not None:
            chart = create_candlestick_chart(selected_code, df_data)
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.warning("无法获取 K 线数据")

def page_trades():
    """交易记录页面"""
    st.title("📝 交易记录")
    
    trades = load_trades()
    
    if not trades:
        st.info("暂无交易记录")
        return
    
    # 转换为 DataFrame
    trade_list = []
    for trade in trades:
        trade_list.append({
            '时间': trade.get('time', '')[:16],
            '股票': trade.get('name', ''),
            '代码': trade.get('code', ''),
            '操作': trade.get('action', ''),
            '股数': trade.get('shares', 0),
            '价格': f"¥{trade.get('price', 0):.2f}",
            '金额': f"¥{trade.get('shares', 0) * trade.get('price', 0):,.2f}",
            '盈亏': f"¥{trade.get('profit', 0):,.2f}" if 'profit' in trade else '-',
        })
    
    df = pd.DataFrame(trade_list)
    
    # 筛选器
    col1, col2 = st.columns(2)
    with col1:
        stock_filter = st.multiselect("筛选股票", options=df['股票'].unique().tolist())
    with col2:
        action_filter = st.multiselect("筛选操作", options=df['操作'].unique().tolist())
    
    if stock_filter:
        df = df[df['股票'].isin(stock_filter)]
    if action_filter:
        df = df[df['操作'].isin(action_filter)]
    
    # 显示表格
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # 统计信息
    st.subheader("📊 交易统计")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总交易次数", len(trades))
    with col2:
        buy_count = len([t for t in trades if '买入' in t.get('action', '') or '加仓' in t.get('action', '')])
        st.metric("买入次数", buy_count)
    with col3:
        sell_count = len(trades) - buy_count
        st.metric("卖出次数", sell_count)

def page_performance():
    """绩效图表页面"""
    st.title("📈 绩效分析")
    
    account = load_account()
    trades = load_trades()
    
    if not account:
        st.error("未找到账户数据")
        return
    
    initial = account.get('initial_capital', 1000000)
    total_assets = account.get('cash', 0)
    positions = account.get('positions', {})
    
    for code, pos in positions.items():
        total_assets += pos.get('shares', 0) * pos.get('current_price', pos.get('avg_price', 0))
    
    total_return = total_assets - initial
    total_return_pct = (total_return / initial * 100) if initial > 0 else 0
    
    # 关键绩效指标
    st.subheader("📊 关键绩效指标")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("初始资金", f"¥{initial:,.2f}")
    with col2:
        st.metric("当前资产", f"¥{total_assets:,.2f}")
    with col3:
        st.metric("绝对收益", f"¥{total_return:,.2f}", delta=f"{total_return_pct:.2f}%")
    with col4:
        # 估算年化（假设运行 30 天）
        annual_return_pct = total_return_pct * (365 / 30)
        st.metric("估算年化", f"{annual_return_pct:.2f}%")
    
    # 资金曲线
    st.subheader("💹 资金曲线")
    perf_chart = create_performance_chart(account, trades)
    st.plotly_chart(perf_chart, use_container_width=True)
    
    # 月度收益
    if trades:
        st.subheader("📅 月度收益分布")
        monthly_data = {}
        for trade in trades:
            month = trade.get('time', '')[:7]
            if month:
                if month not in monthly_data:
                    monthly_data[month] = 0
                profit = trade.get('profit', 0)
                monthly_data[month] += profit
        
        if monthly_data:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=list(monthly_data.keys()),
                y=list(monthly_data.values()),
                marker_color=['#ff4d4f' if v >= 0 else '#52c41a' for v in monthly_data.values()],
                text=[f"¥{v:,.2f}" for v in monthly_data.values()],
                textposition='auto',
            ))
            fig.update_layout(
                xaxis_title='月份',
                yaxis_title='收益 (¥)',
                template='plotly_white',
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

def page_settings():
    """设置页面"""
    st.title("⚙️ 设置")
    
    st.markdown("""
    ### 数据源配置
    
    - **账户文件**: `/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/account_ideal.json`
    - **交易记录**: `/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/交易记录.json`
    - **数据提供商**: 腾讯财经
    
    ### 刷新频率
    
    - 页面数据每 30 秒自动缓存更新
    - 点击"刷新数据"按钮可手动刷新
    
    ### 访问地址
    
    - **本地访问**: http://localhost:8501
    - **局域网访问**: http://<本机 IP>:8501
    
    ### 功能对比
    
    | 功能 | Streamlit | Plotly Dash |
    |------|-----------|-------------|
    | 账户概览 | ✅ | ✅ |
    | 持仓分析 | ✅ | ✅ |
    | 交易记录 | ✅ | ✅ |
    | 绩效图表 | ✅ | ❌ |
    | 多页面导航 | ✅ | ❌ |
    | K 线图表 | ✅ | ✅ |
    | 实时刷新 | ✅ | ✅ |
    """)
    
    if st.button("🗑️ 清除缓存"):
        st.cache_data.clear()
        st.success("缓存已清除，页面将自动刷新")
        st.rerun()

# ==================== 主程序 ====================

def main():
    """主函数"""
    # 页面配置
    st.set_page_config(
        page_title="BobQuant 可视化看板",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # 侧边栏导航
    with st.sidebar:
        st.title("🚀 BobQuant")
        st.markdown("**可视化看板**")
        
        page = st.radio(
            "导航",
            ["📊 账户概览", "📈 持仓分析", "📝 交易记录", "📈 绩效分析", "⚙️ 设置"],
            index=0
        )
        
        st.markdown("---")
        st.markdown("### 状态")
        st.info("✅ 数据正常")
        
        # 最后更新时间
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        st.caption(f"最后更新：{now}")
    
    # 根据选择显示页面
    if page == "📊 账户概览":
        page_overview()
    elif page == "📈 持仓分析":
        page_positions()
    elif page == "📝 交易记录":
        page_trades()
    elif page == "📈 绩效分析":
        page_performance()
    elif page == "⚙️ 设置":
        page_settings()

if __name__ == '__main__':
    main()
