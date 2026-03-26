# -*- coding: utf-8 -*-
"""
Infoway WebSocket A 股调试脚本
测试不同的股票代码格式
"""

import websocket
import json
import time
import threading
from datetime import datetime

# 配置
API_KEY = 'c87ebee1fe204f40acc35ed0272677d3-infoway'
WS_URL = f'wss://data.infoway.io/ws?business=stock&apikey={API_KEY}'

# 测试不同的股票代码格式
STOCK_FORMATS = [
    {
        'name': '格式 1: 代码。市场 (SH/SZ)',
        'codes': '601398.SH,600036.SH,600519.SH,000858.SZ,000333.SZ',
        'stocks': ['工商银行', '招商银行', '贵州茅台', '五粮液', '美的集团']
    },
    {
        'name': '格式 2: 市场。代码',
        'codes': 'SH.601398,SZ.600036,SH.600519,SZ.000858,SZ.000333',
        'stocks': ['工商银行', '招商银行', '贵州茅台', '五粮液', '美的集团']
    },
    {
        'name': '格式 3: 纯代码',
        'codes': '601398,600036,600519,000858,000333',
        'stocks': ['工商银行', '招商银行', '贵州茅台', '五粮液', '美的集团']
    },
    {
        'name': '格式 4: 市场前缀_代码',
        'codes': 'sh601398,sz600036,sh600519,sz000858,sz000333',
        'stocks': ['工商银行', '招商银行', '贵州茅台', '五粮液', '美的集团']
    },
]

# 协议号
PROTOCOL_TRADE = 10000    # 实时成交明细
PROTOCOL_DEPTH = 10003    # 实时盘口数据
PROTOCOL_KLINE = 10006    # K 线数据

# 全局变量
ws = None
connected = False
messages_received = []
test_format_index = 0

def generate_trace_id():
    import uuid
    return str(uuid.uuid4())

def on_message(ws, message):
    """收到消息回调"""
    global messages_received
    messages_received.append(message)
    
    try:
        data = json.loads(message)
        code = data.get('code', 'N/A')
        
        # 如果是订阅确认，继续测试
        if code in [200, 10001, 10004, 10007]:
            print(f"  ✅ 收到确认：code={code}")
        # 如果是实时数据
        elif code in [PROTOCOL_TRADE, PROTOCOL_DEPTH, PROTOCOL_KLINE]:
            print(f"\n🎉 收到实时数据！")
            print(f"  协议号：{code}")
            print(f"  数据：{json.dumps(data, ensure_ascii=False)[:500]}")
        else:
            print(f"  📊 收到消息：code={code}")
            
    except:
        print(f"  📄 收到消息：{message[:100]}")

def on_error(ws, error):
    print(f"\n❌ 错误：{error}")

def on_close(ws, close_status_code, close_msg):
    global connected
    connected = False
    print(f"\n🔴 连接关闭")

def on_open(ws):
    global connected
    connected = True
    print(f"\n🟢 WebSocket 连接成功！")
    
    # 测试当前格式
    format_info = STOCK_FORMATS[test_format_index]
    print(f"\n📡 测试 {format_info['name']}")
    print(f"  股票代码：{format_info['codes']}")
    
    # 发送订阅请求
    time.sleep(1)
    
    # 1. 订阅成交明细
    print(f"\n📡 订阅成交明细 (协议号{PROTOCOL_TRADE})...")
    subscribe_msg = {
        'code': PROTOCOL_TRADE,
        'trace': generate_trace_id(),
        'data': {
            'codes': format_info['codes']
        }
    }
    ws.send(json.dumps(subscribe_msg))
    time.sleep(3)
    
    # 2. 订阅盘口数据
    print(f"\n📡 订阅盘口数据 (协议号{PROTOCOL_DEPTH})...")
    subscribe_msg = {
        'code': PROTOCOL_DEPTH,
        'trace': generate_trace_id(),
        'data': {
            'codes': format_info['codes']
        }
    }
    ws.send(json.dumps(subscribe_msg))
    time.sleep(3)
    
    # 3. 订阅 K 线数据
    print(f"\n📡 订阅 K 线数据 (协议号{PROTOCOL_KLINE})...")
    subscribe_msg = {
        'code': PROTOCOL_KLINE,
        'trace': generate_trace_id(),
        'data': {
            'arr': [
                {
                    'type': 1,
                    'codes': format_info['codes']
                }
            ]
        }
    }
    ws.send(json.dumps(subscribe_msg))
    time.sleep(3)

def test_format(format_index):
    """测试一种股票代码格式"""
    global ws, connected, messages_received, test_format_index
    
    test_format_index = format_index
    messages_received = []
    connected = False
    
    print("\n" + "="*70)
    print(f"🧪 测试格式 {format_index + 1}/4")
    print("="*70)
    print(f"格式名称：{STOCK_FORMATS[format_index]['name']}")
    print(f"股票代码：{STOCK_FORMATS[format_index]['codes']}")
    print("="*70)
    
    # 创建 WebSocket 连接
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # 启动连接
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()
    
    # 等待连接和数据
    print("\n⏳ 等待连接和数据...")
    for i in range(15):
        time.sleep(1)
        if messages_received:
            # 检查是否有实时数据
            has_realtime = False
            for msg in messages_received:
                try:
                    data = json.loads(msg)
                    if data.get('code') in [PROTOCOL_TRADE, PROTOCOL_DEPTH, PROTOCOL_KLINE]:
                        has_realtime = True
                        break
                except:
                    pass
            
            if has_realtime:
                print(f"\n✅ 格式 {format_index + 1} 成功！收到实时数据！")
                return True
    
    print(f"\n⚠️ 格式 {format_index + 1} 未收到实时数据")
    ws.close()
    time.sleep(1)
    return False

def main():
    print("="*70)
    print("🧪 Infoway A 股代码格式调试")
    print("="*70)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Key: {API_KEY[:30]}...")
    print("="*70)
    
    # 测试所有格式
    for i in range(len(STOCK_FORMATS)):
        success = test_format(i)
        
        if success:
            print("\n" + "="*70)
            print(f"🎉 找到正确的格式！")
            print("="*70)
            print(f"格式：{STOCK_FORMATS[i]['name']}")
            print(f"代码：{STOCK_FORMATS[i]['codes']}")
            print("\n建议配置:")
            print(f"""
INFOWAY_CONFIG = {{
    'api_key': '{API_KEY}',
    'websocket_url': '{WS_URL}',
    'stock_format': '{STOCK_FORMATS[i]['codes']}',
    'enabled': True,
}}
            """)
            return
    
    print("\n" + "="*70)
    print("⚠️ 所有格式都未收到实时数据")
    print("="*70)
    print("\n可能需要:")
    print("  1. 联系 Infoway 确认正确的股票代码格式")
    print("  2. 确认 A 股数据权限已开通")
    print("  3. 继续使用腾讯财经")

if __name__ == '__main__':
    main()
