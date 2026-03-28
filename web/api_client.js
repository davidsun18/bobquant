/**
 * BobQuant Web UI - API Client
 * 数据接口封装，UI层只调用此接口获取数据
 */

const APIClient = {
    // 基础配置
    config: {
        baseUrl: '',
        refreshInterval: 5000,  // 交易时间5秒
        idleInterval: 60000,    // 非交易时间60秒
    },

    // 交易时间判断
    isTradingTime() {
        const now = new Date();
        const hour = now.getHours();
        const minute = now.getMinutes();
        const time = hour * 100 + minute;
        return (time >= 915 && time <= 1130) || (time >= 1300 && time <= 1500);
    },

    // 获取刷新间隔
    getRefreshInterval() {
        return this.isTradingTime() ? this.config.refreshInterval : this.config.idleInterval;
    },

    // 获取交易状态
    getTradingStatus() {
        return this.isTradingTime() ? 
            { text: '交易中', color: '#ff4d4f', icon: '🔴' } : 
            { text: '休市中', color: '#52c41a', icon: '🟢' };
    },

    // 格式化金额
    formatMoney(amount) {
        if (amount === null || amount === undefined) return '--';
        return '¥' + amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    },

    // 格式化百分比
    formatPercent(value) {
        if (value === null || value === undefined) return '--';
        return (value >= 0 ? '+' : '') + (value * 100).toFixed(2) + '%';
    },

    // API: 获取账户数据
    async getAccount() {
        try {
            const response = await fetch('/api/account?_=' + new Date().getTime());
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            return {
                totalAssets: data.total_assets,
                marketValue: data.market_value,
                cash: data.cash,
                positionProfit: data.position_profit,
                todayProfit: data.profit_today,
                positions: data.positions || [],
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            console.error('[API] getAccount error:', error);
            return null;
        }
    },

    // API: 获取交易记录
    async getTrades(limit = 20) {
        try {
            const response = await fetch('/api/trades?_=' + new Date().getTime());
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            return (data.trades || []).slice(-limit).reverse().map(trade => ({
                time: trade.time,
                code: trade.code,
                name: trade.name,
                action: trade.action,
                shares: trade.shares,
                price: trade.price,
                amount: trade.shares * trade.price,
                isBuy: trade.action.includes('买入') || trade.action.includes('加仓')
            }));
        } catch (error) {
            console.error('[API] getTrades error:', error);
            return [];
        }
    },

    // API: 获取股票详情
    async getStockDetail(code) {
        try {
            const response = await fetch('/api/stock/' + code + '?_=' + new Date().getTime());
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            return data;
        } catch (error) {
            console.error('[API] getStockDetail error:', error);
            return null;
        }
    }
};

// 导出
window.APIClient = APIClient;
