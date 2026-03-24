# Infoway API 配置（已根据官方文档更新）
# Token: c87ebee1fe204f40acc35ed0272677d3-infoway
# 官网：https://infoway.io
# 文档：https://docs.infoway.io

INFOWAY_CONFIG = {
    # API Key
    'api_key': 'c87ebee1fe204f40acc35ed0272677d3-infoway',
    
    # WebSocket 订阅地址（官方文档）
    'websocket_url': 'wss://data.infoway.io/ws',
    
    # WebSocket 参数
    'websocket_params': {
        'business': 'stock',  # 股票产品（A 股/港股/美股）
        'apikey': 'c87ebee1fe204f40acc35ed0272677d3-infoway',
    },
    
    # 完整的 WebSocket 地址
    'websocket_full_url': 'wss://data.infoway.io/ws?business=stock&apikey=c87ebee1fe204f40acc35ed0272677d3-infoway',
    
    # 查询配置
    'batch_size': 10,  # 每次批量查询 10 只
    'interval_seconds': 15,  # 每 15 秒查询一次
    
    # API 限制（根据套餐）
    'rate_limit_per_minute': 60,  # 60 次/分钟
    'daily_limit': 86400,  # 86400 次/日
    'websocket_subscriptions': 10,  # 10 个 WebSocket 订阅
    
    # 支持的数据类型
    'supports': {
        'websocket': True,  # WebSocket 实时推送 ⭐
        'http_quote': False,  # HTTP 行情（可能不支持）
        'kline': True,  # K 线数据
        'tick': True,  # Tick 数据
        'orderbook': True,  # 盘口数据
    },
    
    # 启用状态
    'enabled': False,  # 先禁用，WebSocket 测试通过后再启用
}
