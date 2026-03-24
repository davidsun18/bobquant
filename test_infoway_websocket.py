# -*- coding: utf-8 -*-
"""
Infoway WebSocket API 测试脚本
根据官方文档配置测试
"""

import websocket
import json
import time
import threading
from datetime import datetime

# 配置
API_KEY = 'c87ebee1fe204f40acc35ed0272677d3-infoway'
WS_URL = f'wss://data.infoway.io/ws?business=stock&apikey={API_KEY}'

# 测试股票（A 股格式）
# Infoway A 股代码格式可能是：601398.SH 或 sh.601398
TEST_STOCKS = [
    '601398.SH',  # 工商银行
    '600036.SH',  # 招商银行
    '600519.SH',  # 贵州茅台
    '000858.SZ',  # 五粮液
    '000333.SZ',  # 美的集团
]

# 全局变量
ws = None
connected = False
received_data = []

def on_message(ws, message):
    """收到消息回调"""
    global received_data
    print(f"\n✅ 收到消息:")
    print(f"  原始数据：{message[:500]}")
    
    try:
        data = json.loads(message)
        received_data.append(data)
        
        print(f"  解析后：{json.dumps(data, indent=2)[:500]}")
    except:
        print(f"  无法解析为 JSON")

def on_error(ws, error):
    """错误回调"""
    print(f"\n❌ 错误：{error}")

def on_close(ws, close_status_code, close_msg):
    """关闭回调"""
    global connected
    connected = False
    print(f"\n🔴 连接关闭：{close_status_code} - {close_msg}")

def on_open(ws):
    """打开回调"""
    global connected
    connected = True
    print(f"\n🟢 WebSocket 连接成功！")
    
    # 订阅股票
    print(f"\n📡 开始订阅股票...")
    subscribe_message = {
        'action': 'subscribe',
        'params': {
            'symbols': ','.join(TEST_STOCKS)
        }
    }
    
    print(f"  订阅消息：{json.dumps(subscribe_message)}")
    ws.send(json.dumps(subscribe_message))
    print(f"  ✅ 已发送订阅请求")

def test_websocket():
    """测试 WebSocket 连接"""
    global ws, connected, received_data
    
    print("="*70)
    print("🧪 Infoway WebSocket API 测试")
    print("="*70)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"WebSocket URL: {WS_URL}")
    print(f"测试股票：{', '.join(TEST_STOCKS)}")
    print("="*70)
    
    # 创建 WebSocket 连接
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # 启动连接（非阻塞）
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()
    
    # 等待连接
    print("\n⏳ 等待连接...")
    for i in range(10):
        time.sleep(1)
        if connected:
            break
        print(f"  等待中... ({i+1}s)")
    
    if not connected:
        print("\n❌ 连接超时失败")
        return False
    
    # 等待数据
    print("\n⏳ 等待实时数据...")
    for i in range(15):
        time.sleep(1)
        if received_data:
            print(f"\n✅ 收到 {len(received_data)} 条数据！")
            break
        print(f"  等待数据... ({i+1}s)")
    
    # 关闭连接
    print("\n🔴 关闭连接...")
    ws.close()
    time.sleep(2)
    
    # 汇总结果
    print("\n" + "="*70)
    print("📊 测试结果")
    print("="*70)
    
    if connected and received_data:
        print("✅ WebSocket 连接成功！")
        print(f"✅ 收到 {len(received_data)} 条实时数据")
        print("\n建议配置:")
        print(f"""
INFOWAY_CONFIG = {{
    'api_key': '{API_KEY}',
    'websocket_url': '{WS_URL}',
    'enabled': True,
}}
        """)
        return True
    else:
        print("❌ WebSocket 测试失败")
        print("\n可能原因:")
        print("  1. API Key 无效")
        print("  2. WebSocket 服务不可用")
        print("  3. 网络问题/防火墙")
        print("  4. 股票代码格式不对")
        return False

def main():
    success = test_websocket()
    
    if success:
        print("\n" + "="*70)
        print("🎉 Infoway WebSocket 可用！")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("⚠️ 建议继续使用腾讯财经")
        print("="*70)

if __name__ == '__main__':
    main()
