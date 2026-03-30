#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化模拟盘进程守护脚本
监控关键进程，自动重启崩溃的服务
支持开机自启动（通过 systemd 或 crontab）

用法:
    python3 process_guard.py          # 前台运行
    python3 process_guard.py --daemon # 后台守护模式
"""

import os
import sys
import time
import signal
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# 配置
SCRIPT_DIR = Path(__file__).parent.absolute()
LOG_DIR = SCRIPT_DIR / "logs"
PID_FILE = SCRIPT_DIR / "logs" / "process_guard.pid"
GUARD_LOG = LOG_DIR / "process_guard.log"

# 需要守护的进程配置
PROCESSES = [
    {
        "name": "Web UI",
        "pattern": "web_ui.py",
        "command": "python3 web_ui.py",
        "log_file": "logs/web_ui.log",
        "enabled": True,
    },
    {
        "name": "BobQuant 主进程",
        "pattern": "bobquant/main.py",
        "command": "python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation",
        "log_file": "logs/bobquant.log",
        "enabled": True,
    },
    {
        "name": "中频交易",
        "pattern": "run_medium_frequency.py",
        "command": "PYTHONUNBUFFERED=1 python3 scripts/run_medium_frequency.py --config medium_frequency/config/mf_config.yaml --dry-run",
        "log_file": "logs/medium_frequency_run.log",
        "enabled": True,
    },
]

# 全局变量
running = True


def log(message):
    """日志输出"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    
    # 写入日志文件
    try:
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except Exception as e:
        print(f"写入日志失败：{e}")


def check_process(pattern):
    """检查进程是否运行"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def get_process_pid(pattern):
    """获取进程 PID"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return int(result.stdout.strip().split("\n")[0])
    except Exception:
        pass
    return None


def start_process(proc_config):
    """启动进程"""
    name = proc_config["name"]
    command = proc_config["command"]
    log_file = proc_config["log_file"]
    
    try:
        log(f"🔄 启动 {name}...")
        
        # 确保日志目录存在
        log_path = SCRIPT_DIR / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 启动进程
        with open(log_path, "a", encoding="utf-8") as f:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=str(SCRIPT_DIR),
                stdout=f,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )
        
        time.sleep(2)
        
        if check_process(proc_config["pattern"]):
            pid = get_process_pid(proc_config["pattern"])
            log(f"✅ {name} 启动成功 (PID: {pid})")
            return True
        else:
            log(f"❌ {name} 启动失败")
            return False
            
    except Exception as e:
        log(f"❌ 启动 {name} 异常：{e}")
        return False


def restart_process(proc_config):
    """重启进程"""
    name = proc_config["name"]
    pattern = proc_config["pattern"]
    
    log(f"⚠️  {name} 未运行，尝试重启...")
    
    # 先清理可能存在的僵尸进程
    try:
        subprocess.run(
            ["pkill", "-f", pattern],
            capture_output=True,
            timeout=5
        )
        time.sleep(1)
    except Exception:
        pass
    
    # 启动新进程
    return start_process(proc_config)


def signal_handler(signum, frame):
    """信号处理"""
    global running
    log(f"\n⏹️  收到信号 {signum}，停止守护...")
    running = False


def write_pid_file():
    """写入 PID 文件"""
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        log(f"写入 PID 文件失败：{e}")


def remove_pid_file():
    """删除 PID 文件"""
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception as e:
        log(f"删除 PID 文件失败：{e}")


def guard_loop():
    """守护循环"""
    global running
    
    log("=" * 60)
    log("🛡️  进程守护启动")
    log("=" * 60)
    log(f"工作目录：{SCRIPT_DIR}")
    log(f"日志目录：{LOG_DIR}")
    log(f"守护进程数：{len([p for p in PROCESSES if p['enabled']])}")
    log("=" * 60)
    
    # 写入 PID 文件
    write_pid_file()
    
    # 初始启动所有进程
    log("\n📊 初始启动检查...")
    for proc in PROCESSES:
        if proc["enabled"]:
            if not check_process(proc["pattern"]):
                start_process(proc)
            else:
                pid = get_process_pid(proc["pattern"])
                log(f"✅ {proc['name']} 已运行 (PID: {pid})")
    
    log("\n🔄 开始守护循环 (每 30 秒检查一次)...")
    
    check_count = 0
    while running:
        try:
            check_count += 1
            
            # 定期检查所有进程
            for proc in PROCESSES:
                if not proc["enabled"]:
                    continue
                
                if not check_process(proc["pattern"]):
                    log(f"\n❌ 检测到 {proc['name']} 已退出!")
                    restart_process(proc)
            
            # 每小时输出一次状态
            if check_count % 120 == 0:  # 30 秒 * 120 = 1 小时
                log(f"\n💓 心跳检查 - 已运行 {check_count // 120} 小时")
                for proc in PROCESSES:
                    if proc["enabled"]:
                        status = "✅" if check_process(proc["pattern"]) else "❌"
                        log(f"  {status} {proc['name']}")
            
            time.sleep(30)
            
        except KeyboardInterrupt:
            log("\n⏹️  用户中断")
            break
        except Exception as e:
            log(f"❌ 守护循环异常：{e}")
            time.sleep(5)
    
    # 清理
    log("\n🛑 守护停止")
    remove_pid_file()


def daemonize():
    """守护进程化（后台运行）"""
    # 第一次 fork
    pid = os.fork()
    if pid > 0:
        print(f"守护进程已启动 (PID: {pid})")
        sys.exit(0)
    
    # 创建新会话
    os.setsid()
    
    # 第二次 fork
    pid = os.fork()
    if pid > 0:
        sys.exit(0)
    
    # 重定向标准输入输出
    sys.stdin = open("/dev/null", "r")
    sys.stdout = open(GUARD_LOG, "a", encoding="utf-8")
    sys.stderr = sys.stdout
    
    # 更改工作目录
    os.chdir(SCRIPT_DIR)
    
    # 写入 PID 文件
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    
    # 运行守护循环
    guard_loop()


def status():
    """显示状态"""
    print("=" * 60)
    print("📊 进程守护状态")
    print("=" * 60)
    
    # 检查守护进程
    if PID_FILE.exists():
        try:
            with open(PID_FILE) as f:
                guard_pid = int(f.read().strip())
            if check_process(str(guard_pid)):
                print(f"✅ 守护进程运行中 (PID: {guard_pid})")
            else:
                print(f"⚠️  守护进程已停止 (PID 文件残留)")
        except Exception:
            print("⚠️  无法读取守护进程状态")
    else:
        print("⏸️  守护进程未运行")
    
    print("\n📋 受保护进程:")
    for proc in PROCESSES:
        if not proc["enabled"]:
            continue
        
        status_icon = "✅" if check_process(proc["pattern"]) else "❌"
        pid = get_process_pid(proc["pattern"])
        pid_str = f"(PID: {pid})" if pid else "(未运行)"
        print(f"  {status_icon} {proc['name']} {pid_str}")
    
    print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="量化模拟盘进程守护")
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="后台守护模式"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="显示状态"
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="停止守护"
    )
    
    args = parser.parse_args()
    
    # 确保日志目录存在
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    if args.status:
        status()
        return
    
    if args.stop:
        if PID_FILE.exists():
            try:
                with open(PID_FILE) as f:
                    guard_pid = int(f.read().strip())
                os.kill(guard_pid, signal.SIGTERM)
                print(f"✅ 已停止守护进程 (PID: {guard_pid})")
                PID_FILE.unlink()
            except Exception as e:
                print(f"❌ 停止失败：{e}")
        else:
            print("⏸️  守护进程未运行")
        return
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if args.daemon:
        daemonize()
    else:
        guard_loop()


if __name__ == "__main__":
    main()
