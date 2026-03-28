/**
 * BobQuant Web UI - UI Renderer
 * 纯UI渲染层，只负责展示，不处理数据逻辑
 */

const UIRenderer = {
    // 渲染资产概览
    renderAssets(data) {
        if (!data) return;
        
        const setValue = (id, value, isProfit = false) => {
            const el = document.getElementById(id);
            if (!el) return;
            
            if (isProfit && value !== null) {
                const isPositive = value >= 0;
                el.className = `asset-value ${isPositive ? 'profit' : 'loss'}`;
                el.textContent = (isPositive ? '+' : '') + APIClient.formatMoney(value);
            } else {
                el.textContent = APIClient.formatMoney(value);
            }
        };

        setValue('totalAssets', data.totalAssets);
        setValue('marketValue', data.marketValue);
        setValue('cash', data.cash);
        setValue('positionProfit', data.positionProfit, true);
        setValue('todayProfit', data.todayProfit, true);
    },

    // 渲染持仓明细 (桌面版表格)
    renderPositionsTable(positions) {
        const tbody = document.getElementById('positionsContent');
        if (!tbody) return;

        if (!positions || positions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty-cell">暂无持仓</td></tr>';
            return;
        }

        tbody.innerHTML = positions.map(pos => {
            const profit = pos.profit || 0;
            const profitClass = profit >= 0 ? 'profit' : 'loss';
            const profitText = profit >= 0 ? '+' : '';
            const marketValue = (pos.shares || 0) * (pos.current_price || 0);
            
            return `
                <tr>
                    <td class="code-cell">${pos.code || '--'}</td>
                    <td class="name-cell">${pos.name || '--'}</td>
                    <td>${pos.shares || 0}</td>
                    <td>¥${(pos.avg_price || 0).toFixed(2)}</td>
                    <td>¥${(pos.current_price || 0).toFixed(2)}</td>
                    <td>${APIClient.formatMoney(marketValue)}</td>
                    <td class="profit-cell ${profitClass}">${profitText}${APIClient.formatMoney(profit)}</td>
                    <td class="percent-cell ${profitClass}">${APIClient.formatPercent(pos.profit_pct)}</td>
                </tr>
            `;
        }).join('');
    },

    // 渲染持仓明细 (手机版卡片)
    renderPositionsMobile(positions) {
        const container = document.getElementById('mobilePositionsContent');
        if (!container) return;

        if (!positions || positions.length === 0) {
            container.innerHTML = '<div class="empty-cell">暂无持仓</div>';
            return;
        }

        container.innerHTML = positions.map(pos => {
            const profit = pos.profit || 0;
            const profitClass = profit >= 0 ? '' : 'loss';
            const profitText = profit >= 0 ? '+' : '';
            const tradableShares = (pos.shares || 0) - (pos.today_bought || 0);
            
            return `
                <div class="mobile-position-card ${profitClass}">
                    <div class="mobile-position-header">
                        <div>
                            <div class="mobile-stock-name">${pos.name || '--'}</div>
                            <div class="mobile-stock-code">${pos.code || '--'}</div>
                        </div>
                        <div class="mobile-profit">
                            <div class="mobile-profit-value ${profitClass}">${profitText}${APIClient.formatMoney(profit)}</div>
                            <div class="mobile-profit-percent">${APIClient.formatPercent(pos.profit_pct)}</div>
                        </div>
                    </div>
                    <div class="mobile-position-grid">
                        <div class="mobile-stat-item">
                            <span class="mobile-stat-label">持仓</span>
                            <span class="mobile-stat-value">${pos.shares || 0}</span>
                        </div>
                        <div class="mobile-stat-item">
                            <span class="mobile-stat-label">可交易</span>
                            <span class="mobile-stat-value">${tradableShares}</span>
                        </div>
                        <div class="mobile-stat-item">
                            <span class="mobile-stat-label">现价</span>
                            <span class="mobile-stat-value">¥${(pos.current_price || 0).toFixed(2)}</span>
                        </div>
                        <div class="mobile-stat-item">
                            <span class="mobile-stat-label">成本</span>
                            <span class="mobile-stat-value">¥${(pos.avg_price || 0).toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    },

    // 渲染交易记录 (桌面版表格)
    renderTradesTable(trades) {
        const tbody = document.getElementById('tradesContent');
        if (!tbody) return;

        if (!trades || trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-cell">暂无交易记录</td></tr>';
            return;
        }

        tbody.innerHTML = trades.map(trade => {
            const actionClass = trade.isBuy ? 'action-buy' : 'action-sell';
            const actionText = trade.action.includes('卖出') ? '卖出' : trade.action;
            
            let dateStr = trade.time || '--';
            let timeOnly = '';
            if (trade.time && trade.time.includes(' ')) {
                const parts = trade.time.split(' ');
                dateStr = parts[0];
                timeOnly = parts[1].substring(0, 5);
            }
            
            return `
                <tr>
                    <td class="time-cell">${dateStr}<br>${timeOnly}</td>
                    <td>${trade.name || '--'}</td>
                    <td class="${actionClass}">${actionText}</td>
                    <td>${trade.shares || 0}</td>
                    <td>¥${(trade.price || 0).toFixed(2)}</td>
                    <td>${APIClient.formatMoney(trade.amount)}</td>
                </tr>
            `;
        }).join('');
    },

    // 渲染交易记录 (手机版卡片)
    renderTradesMobile(trades) {
        const container = document.getElementById('mobileTradesContent');
        if (!container) return;

        if (!trades || trades.length === 0) {
            container.innerHTML = '<div class="empty-cell">暂无交易记录</div>';
            return;
        }

        container.innerHTML = trades.map(trade => {
            const actionClass = trade.isBuy ? 'mobile-action-buy' : 'mobile-action-sell';
            const actionText = trade.action.includes('卖出') ? '卖出' : trade.action;
            
            let dateStr = trade.time || '--';
            let timeOnly = '';
            if (trade.time && trade.time.includes(' ')) {
                const parts = trade.time.split(' ');
                dateStr = parts[0];
                timeOnly = parts[1].substring(0, 5);
            }
            
            return `
                <div class="mobile-trade-card">
                    <div class="mobile-trade-header">
                        <span class="mobile-trade-time">${dateStr} ${timeOnly}</span>
                        <span class="mobile-trade-action ${actionClass}">${actionText}</span>
                    </div>
                    <div class="mobile-trade-body">
                        <span class="mobile-trade-stock">${trade.name || '--'}</span>
                        <div class="mobile-trade-details">
                            <span class="mobile-trade-shares">${trade.shares || 0}股</span>
                            <span class="mobile-trade-price">¥${(trade.price || 0).toFixed(2)}</span>
                            <span class="mobile-trade-amount">${APIClient.formatMoney(trade.amount)}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    },

    // 渲染更新时间
    renderUpdateTime() {
        const now = new Date();
        const timeStr = now.getFullYear() + '-' + 
                       String(now.getMonth() + 1).padStart(2, '0') + '-' + 
                       String(now.getDate()).padStart(2, '0') + ' ' + 
                       String(now.getHours()).padStart(2, '0') + ':' + 
                       String(now.getMinutes()).padStart(2, '0') + ':' + 
                       String(now.getSeconds()).padStart(2, '0');
        
        const status = APIClient.getTradingStatus();
        
        const el = document.getElementById('updateTime');
        if (el) {
            el.innerHTML = `最后更新：${timeStr} <span style="margin-left: 10px; color: ${status.color};">${status.icon} ${status.text}</span>`;
        }
    },

    // 渲染所有数据
    renderAll(accountData, tradesData) {
        this.renderAssets(accountData);
        this.renderPositionsTable(accountData?.positions);
        this.renderPositionsMobile(accountData?.positions);
        this.renderTradesTable(tradesData);
        this.renderTradesMobile(tradesData);
        this.renderUpdateTime();
    }
};

// 导出
window.UIRenderer = UIRenderer;
