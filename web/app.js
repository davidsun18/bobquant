/**
 * BobQuant Web UI - Main Application
 * 主应用控制器，协调API和UI
 */

const BobQuantApp = {
    // 数据缓存
    cache: {
        account: null,
        trades: null,
        lastUpdate: null
    },

    // 刷新定时器
    refreshTimer: null,

    // 初始化
    async init() {
        console.log('[BobQuant] 初始化应用...');
        
        // 首次加载数据
        await this.loadData();
        
        // 启动自动刷新
        this.scheduleRefresh();
        
        console.log('[BobQuant] 应用初始化完成');
    },

    // 加载数据
    async loadData() {
        try {
            // 并行获取数据
            const [account, trades] = await Promise.all([
                APIClient.getAccount(),
                APIClient.getTrades(20)
            ]);

            if (account) {
                this.cache.account = account;
                this.cache.lastUpdate = new Date();
            }

            if (trades) {
                this.cache.trades = trades;
            }

            // 渲染UI
            UIRenderer.renderAll(this.cache.account, this.cache.trades);

        } catch (error) {
            console.error('[BobQuant] 加载数据失败:', error);
        }
    },

    // 手动刷新
    async refresh() {
        console.log('[BobQuant] 手动刷新...');
        await this.loadData();
    },

    // 定时刷新
    scheduleRefresh() {
        if (this.refreshTimer) {
            clearTimeout(this.refreshTimer);
        }

        const interval = APIClient.getRefreshInterval();
        console.log(`[BobQuant] 下次刷新: ${interval/1000}秒后`);

        this.refreshTimer = setTimeout(async () => {
            await this.loadData();
            this.scheduleRefresh();
        }, interval);
    },

    // 获取缓存数据
    getCache() {
        return this.cache;
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    BobQuantApp.init();
});

// 导出
window.BobQuantApp = BobQuantApp;
