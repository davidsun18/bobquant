"""
BobQuant V2 Web 服务
提供统一的 REST API 接口
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sys
import time
import requests
from functools import wraps

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import AccountAPI, TradeAPI, MarketAPI

app = Flask(__name__)
CORS(app)

# 禁用缓存
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# 初始化 API
account_api = AccountAPI()
trade_api = TradeAPI()
market_api = MarketAPI()

# ========== 重试装饰器 ==========
def retry_on_failure(max_attempts=3, delay=1):
    """API 请求失败重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


# ========== 健康检查端点 ==========
@app.route('/api/health')
def health_check():
    """
    健康检查端点
    检查所有核心组件状态
    """
    status = {
        'status': 'healthy',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'components': {}
    }
    
    # 检查账户 API
    try:
        data = account_api.get()
        status['components']['account_api'] = 'ok' if data else 'warning'
    except Exception as e:
        status['components']['account_api'] = 'error'
        status['status'] = 'degraded'
    
    # 检查交易 API
    try:
        data = trade_api.get(limit=1)
        status['components']['trade_api'] = 'ok'
    except Exception as e:
        status['components']['trade_api'] = 'error'
        status['status'] = 'degraded'
    
    # 检查行情 API
    try:
        quote = market_api.get('sh.600519')
        status['components']['market_api'] = 'ok' if quote else 'warning'
    except Exception as e:
        status['components']['market_api'] = 'error'
        status['status'] = 'degraded'
    
    # 检查交易时间
    status['is_trading_time'] = market_api.is_trading_time()
    
    return jsonify(status)


@app.route('/api/account')
@retry_on_failure(max_attempts=3, delay=0.5)
def get_account():
    """获取账户数据"""
    try:
        data = account_api.get()
        if data:
            return jsonify(data)
        return jsonify({'error': 'No data available'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/trades')
@retry_on_failure(max_attempts=3, delay=0.5)
def get_trades():
    """获取交易记录"""
    try:
        limit = request.args.get('limit', 50, type=int)
        data = trade_api.get(limit=limit)
        return jsonify({'trades': data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/trades/stats')
@retry_on_failure(max_attempts=3, delay=0.5)
def get_trade_stats():
    """获取交易统计"""
    try:
        stats = trade_api.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/market/<code>')
@retry_on_failure(max_attempts=3, delay=0.5)
def get_market_quote(code):
    """获取股票行情"""
    try:
        data = market_api.get(code)
        if data:
            return jsonify(data)
        return jsonify({'error': f'Quote not found for {code}'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/market/batch')
@retry_on_failure(max_attempts=3, delay=0.5)
def get_market_batch():
    """批量获取行情"""
    try:
        codes = request.args.get('codes', '').split(',')
        codes = [c.strip() for c in codes if c.strip()]
        
        if not codes:
            return jsonify({'error': 'No codes provided'}), 400
        
        data = market_api.get_batch(codes)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status')
def get_status():
    """获取系统状态"""
    return jsonify({
        'is_trading_time': market_api.is_trading_time(),
        'version': '2.0.0'
    })


@app.route('/')
def index():
    """API 文档"""
    return jsonify({
        'name': 'BobQuant V2 API',
        'version': '2.0.0',
        'endpoints': {
            '/api/account': '获取账户数据',
            '/api/trades': '获取交易记录 (参数：limit)',
            '/api/trades/stats': '获取交易统计',
            '/api/market/<code>': '获取股票行情',
            '/api/market/batch?codes=xxx,yyy': '批量获取行情',
            '/api/status': '获取系统状态',
            '/api/health': '健康检查（新增）'
        },
        'features': {
            'retry_mechanism': 'API 失败自动重试（最多 3 次）',
            'health_check': '实时监控系统状态',
            'cors_enabled': '支持跨域访问'
        }
    })


def run_server(host='0.0.0.0', port=5000, debug=False):
    """运行服务器"""
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server()
