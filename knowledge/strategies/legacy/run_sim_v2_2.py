#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant 模拟盘启动脚本 v2.2
30 只龙头股精选池
"""
import sys
import os
import time
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("🚀 BobQuant 模拟盘 v2.2 启动中...")
print("=" * 60)
print()

# 检查配置
config_file = os.path.join(os.path.dirname(__file__), 'config', 'sim_config_v2_2.yaml')
pool_file = os.path.join(os.path.dirname(__file__), 'config', 'stock_pool_30_top.yaml')

print("📄 检查配置文件...")
if os.path.exists(config_file):
    print(f"✅ 配置文件：config/sim_config_v2_2.yaml")
else:
    print(f"❌ 配置文件不存在：{config_file}")
    sys.exit(1)

print("📊 检查股票池...")
if os.path.exists(pool_file):
    print(f"✅ 股票池：config/stock_pool_30_top.yaml (30 只龙头股)")
else:
    print(f"❌ 股票池不存在：{pool_file}")
    sys.exit(1)

# 创建日志目录
log_dir = os.path.join(os.path.dirname(__file__), 'logs', 'sim_trading')
os.makedirs(log_dir, exist_ok=True)
print(f"✅ 日志目录：{log_dir}")
print()

# 显示配置摘要
print("=" * 60)
print("📋 模拟盘配置摘要")
print("=" * 60)
print("  版本：v2.2 (30 只龙头股精选池)")
print("  初始资金：1,000,000 元")
print("  单票仓位：≤10%")
print("  最大持仓：≤10 只")
print("  股票池：30 只龙头股")
print("  基本面筛选：ROE≥12%、PE≤30、市值≥200 亿")
print("  策略：双 MACD + 动态布林带")
print("  止损：-8%")
print("  止盈：5%/10%/15% 分批")
print("  大盘风控：启用")
print("=" * 60)
print()

# 导入并运行
print("🚀 加载交易引擎...")
try:
    from main import run_check
    print("✅ 交易引擎加载成功")
    print()
    
    # 运行首次检查
    print("📈 执行首次信号检查...")
    print()
    run_check()
    
    print()
    print("=" * 60)
    print("✅ 模拟盘 v2.2 启动完成！")
    print("=" * 60)
    print()
    print("📊 下一个检查时间：10 秒后")
    print("📝 日志文件：logs/sim_trading/")
    print()
    
except Exception as e:
    print(f"❌ 加载失败：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
