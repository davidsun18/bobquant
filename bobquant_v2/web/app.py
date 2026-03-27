"""
BobQuant V2 Web服务
提供统一的REST API接口
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import AccountAPI, TradeAPI, MarketAPI

app = Flask(__name__)
CORS(app)

# 禁用缓存
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# 初始化API
account_api = AccountAPI()
trade_api = TradeAPI()
market_api = MarketAPI()


@app.route('/api/account')
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
def get_trades():
    """获取交易记录"""
    try:
        limit = request.args.get('limit', 50, type=int)
        data = trade_api.get(limit=limit)
        return jsonify({'trades': data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/trades/stats')
def get_trade_stats():
    """获取交易统计"""
    try:
        stats = trade_api.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/market/<code>')
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
    """API文档"""
    return jsonify({
        'name': 'BobQuant V2 API',
        'version': '2.0.0',
        'endpoints': {
            '/api/account': '获取账户数据',
            '/api/trades': '获取交易记录 (参数: limit)',
            '/api/trades/stats': '获取交易统计',
            '/api/market/<code>': '获取股票行情',
            '/api/market/batch?codes=xxx,yyy': '批量获取行情',
            '/api/status': '获取系统状态'
        }
    })


def run_server(host='0.0.0.0', port=5000, debug=False):
    """运行服务器"""
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server()
