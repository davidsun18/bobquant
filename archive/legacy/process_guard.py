# -*- coding: utf-8 -*-
"""
BOB 量化系统 - 进程守护
确保 Web UI 和模拟盘进程始终运行
"""

import subprocess
import time
import os
import signal
import sys
from datetime import datetime

# 配置
SERVICES = [
    {
        'name': '模拟盘 Web UI',
        'command': ['python3', '/home/openclaw/.openclaw/workspace/quant_strategies/web_ui.py'],
        'port': 5000,
        'check_url': 'http://localhost:5000/',
    },
    {
        'name': '量化交易 UI',
        'command': ['streamlit', 'run', '/home/openclaw/.openclaw/workspace/quant_system/ui/app.py', '--server.port', '8501', '--server.headless', 'true'],
        'port': 8501,
        'check_url': 'http://localhost:8501/',
    },
    {
        'name': '模拟盘交易引擎',
        'command': ['python3', '/home/openclaw/.openclaw/workspace/quant_strategies/run.py'],
        'port': None,  # 无端口，按进程名检测
        'process_keyword': 'run.py',
        'trading_hours_only': True,  # 仅交易时段运行
    },
]

CHECK_INTERVAL = 30  # 每 30 秒检查一次
LOG_FILE = '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/guard.log'

processes = {}

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{timestamp}] {msg}'
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass

def is_port_in_use(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def is_process_running(keyword):
    """检查指定关键字的进程是否在运行"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', keyword],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except:
        return False

def is_trading_hours():
    """判断当前是否为 A 股交易时段"""
    now = datetime.now()
    # 周末不交易
    if now.weekday() >= 5:
        return False
    hour, minute = now.hour, now.minute
    t = hour * 60 + minute
    # 上午 09:25-11:35（提前5分钟启动，晚5分钟收尾）
    # 下午 12:55-15:05
    return (565 <= t <= 695) or (775 <= t <= 905)

def stop_trading_process(service):
    """停止交易进程"""
    keyword = service.get('process_keyword', '')
    name = service['name']
    try:
        result = subprocess.run(
            ['pkill', '-f', keyword],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            log(f'  🛑 {name} 已停止（非交易时段）')
    except:
        pass

def start_service(service):
    name = service['name']
    port = service.get('port')
    keyword = service.get('process_keyword', '')
    trading_only = service.get('trading_hours_only', False)

    # 交易时段限制的服务
    if trading_only:
        if not is_trading_hours():
            # 非交易时段：如果还在跑就停掉
            if keyword and is_process_running(keyword):
                stop_trading_process(service)
            return
        # 交易时段：按进程关键字检测
        if keyword and is_process_running(keyword):
            log(f'  ✅ {name} 已在运行')
            return
    else:
        # 普通服务：按端口检测
        if port and is_port_in_use(port):
            log(f'  ✅ {name} 已在运行 (端口 {port})')
            return
    
    log(f'  🚀 启动 {name}...')
    try:
        # 交易引擎输出到日志文件
        if trading_only:
            trading_log = '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/模拟盘日志.log'
            log_f = open(trading_log, 'a')
            proc = subprocess.Popen(
                service['command'],
                stdout=log_f,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        else:
            proc = subprocess.Popen(
                service['command'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        processes[name] = proc
        time.sleep(5)
        
        if trading_only:
            if is_process_running(keyword):
                log(f'  ✅ {name} 启动成功 (PID: {proc.pid})')
            else:
                log(f'  ⚠️ {name} 启动中...')
        elif port and is_port_in_use(port):
            log(f'  ✅ {name} 启动成功 (PID: {proc.pid})')
        else:
            log(f'  ⚠️ {name} 启动中...')
    except Exception as e:
        log(f'  ❌ {name} 启动失败: {e}')

def check_all():
    for service in SERVICES:
        start_service(service)

def signal_handler(sig, frame):
    log('⚠️ 收到停止信号，关闭守护进程...')
    for name, proc in processes.items():
        try:
            proc.terminate()
            log(f'  已停止 {name}')
        except:
            pass
    sys.exit(0)

def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    log('='*50)
    log('🛡️ BOB 量化系统 - 进程守护启动')
    log(f'监控服务: {len(SERVICES)} 个')
    log(f'检查间隔: {CHECK_INTERVAL} 秒')
    log('='*50)
    
    while True:
        check_all()
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
