# -*- coding: utf-8 -*-
"""
Infoway WebSocket API 正确测试脚本
根据官方文档 Java 代码示例配置
"""

import websocket
import json
import time
import threading
from datetime import datetime

# 配置
API_KEY = 'c87ebee1fe204f40acc35ed0272677d3-infoway'
WS_URL = f'wss://data.infoway.io/ws?business=stock&apikey={API_KEY}'

# 测试股票（A 股格式：代码。市场）
TEST_STOCKS = '601398.SH,600036.SH,600519.SH'

# 协议号（根据官方文档）
PROTOCOL_TRADE = 10000    # 实时成交明细
PROTOCOL_DEPTH = 10003    # 实时盘口数据
PROTOCOL_KLINE = 10006    # K 线数据
PROTOCOL_HEARTBEAT = 10010  # 心跳

# 全局变量
ws = None
connected = False
message_count = 0
received_messages = []

def generate_trace_id():
    """生成 trace ID"""
    import uuid
    return str(uuid.uuid4())

def on_message(ws, message):
    """收到消息回调"""
    global message_count, received_messages
    message_count += 1
    
    print(f"\n✅ 收到消息 #{message_count}:")
    print(f"  原始数据：{message[:300]}")
    
    try:
        data = json.loads(message)
        received_messages.append(data)
        
        code = data.get('code', 'N/A')
        trace = data.get('trace', 'N/A')
        
        print(f"  协议号：{code}")
        print(f"  Trace: {trace}")
        
        # 根据协议号区分消息类型
        if code == PROTOCOL_TRADE:
            print(f"  📊 类型：成交明细数据")
        elif code == PROTOCOL_DEPTH:
            print(f"  📊 类型：盘口数据")
        elif code == PROTOCOL_KLINE:
            print(f"  📊 类型：K 线数据")
        elif code == PROTOCOL_HEARTBEAT:
            print(f"  💓 类型：心跳响应")
        else:
            print(f"  ❓ 类型：未知协议号")
            
    except Exception as e:
        print(f"  解析错误：{e}")

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
    print(f"  Session ID: {ws.sock.id if hasattr(ws.sock, 'id') else 'N/A'}")
    
    # 等待一下再发送订阅
    time.sleep(1)
    
    # 1. 订阅实时成交明细（协议号 10000）
    print(f"\n📡 发送订阅请求 1/3: 成交明细")
    send_subscribe(ws, PROTOCOL_TRADE, TEST_STOCKS)
    time.sleep(2)
    
    # 2. 订阅实时盘口数据（协议号 10003）
    print(f"\n📡 发送订阅请求 2/3: 盘口数据")
    send_subscribe(ws, PROTOCOL_DEPTH, TEST_STOCKS)
    time.sleep(2)
    
    # 3. 订阅 K 线数据（协议号 10006）
    print(f"\n📡 发送订阅请求 3/3: K 线数据")
    send_kline_subscribe(ws, PROTOCOL_KLINE, TEST_STOCKS)
    
    # 4. 启动心跳（5 秒后开始）
    print(f"\n💓 5 秒后开始心跳...")
    threading.Thread(target=start_heartbeat, args=(ws,), daemon=True).start()

def send_subscribe(ws, code, codes):
    """发送订阅请求"""
    subscribe_msg = {
        'code': code,
        'trace': generate_trace_id(),
        'data': {
            'codes': codes
        }
    }
    
    print(f"  发送：{json.dumps(subscribe_msg)}")
    ws.send(json.dumps(subscribe_msg))

def send_kline_subscribe(ws, code, codes):
    """发送 K 线订阅请求"""
    subscribe_msg = {
        'code': code,
        'trace': generate_trace_id(),
        'data': {
            'arr': [
                {
                    'type': 1,  # 1 分钟 K 线
                    'codes': codes
                }
            ]
        }
    }
    
    print(f"  发送：{json.dumps(subscribe_msg)}")
    ws.send(json.dumps(subscribe_msg))

def start_heartbeat(ws):
    """心跳任务"""
    time.sleep(5)  # 先等 5 秒
    
    while connected:
        try:
            heartbeat_msg = {
                'code': PROTOCOL_HEARTBEAT,
                'trace': generate_trace_id()
            }
            print(f"\n💓 发送心跳：{json.dumps(heartbeat_msg)}")
            ws.send(json.dumps(heartbeat_msg))
            time.sleep(30)  # 30 秒一次
        except:
            break

def test_websocket():
    """测试 WebSocket 连接"""
    global ws, connected, message_count, received_messages
    
    print("="*70)
    print("🧪 Infoway WebSocket API 测试 (根据官方文档)")
    print("="*70)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"WebSocket URL: {WS_URL}")
    print(f"测试股票：{TEST_STOCKS}")
    print(f"协议号:")
    print(f"  - 成交明细：{PROTOCOL_TRADE}")
    print(f"  - 盘口数据：{PROTOCOL_DEPTH}")
    print(f"  - K 线数据：{PROTOCOL_KLINE}")
    print(f"  - 心跳：{PROTOCOL_HEARTBEAT}")
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
    print("\n⏳ 等待连接建立...")
    for i in range(10):
        time.sleep(1)
        if connected:
            break
        print(f"  等待中... ({i+1}s)")
    
    if not connected:
        print("\n❌ 连接超时失败")
        return False
    
    # 等待数据
    print("\n⏳ 等待实时数据推送...")
    for i in range(20):
        time.sleep(1)
        if message_count > 0:
            print(f"\n✅ 收到 {message_count} 条数据！")
            break
        print(f"  等待数据... ({i+1}s)")
    
    # 汇总结果
    print("\n" + "="*70)
    print("📊 测试结果")
    print("="*70)
    
    if connected and message_count > 0:
        print("✅ WebSocket 连接成功！")
        print(f"✅ 收到 {message_count} 条实时数据")
        print(f"✅ 数据推送正常")
        print("\n🎉 Infoway WebSocket 可用！")
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
        print("🎉 Infoway WebSocket 配置成功！")
        print("="*70)
        print("\n建议配置:")
        print(f"""
INFOWAY_CONFIG = {{
    'api_key': '{API_KEY}',
    'websocket_url': '{WS_URL}',
    'enabled': True,
}}
        """)
    else:
        print("\n" + "="*70)
        print("⚠️ 建议继续使用腾讯财经")
        print("="*70)

if __name__ == '__main__':
    main()
