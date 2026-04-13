#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 Akshare 获取完整行情数据"""
import akshare as ak
import pandas as pd

print("=== 大东南 (002263) - 完整行情数据 ===\n")

# 方法 1: 东方财富个股详情（获取市值等）
print("[1] 个股基本信息")
try:
    df_info = ak.stock_individual_info_em(symbol="002263")
    info_dict = dict(zip(df_info['item'], df_info['value']))
    print(f"  最新价：{info_dict.get('最新', 'N/A')}")
    print(f"  总市值：{info_dict.get('总市值', 'N/A')}")
    print(f"  流通市值：{info_dict.get('流通市值', 'N/A')}")
    print(f"  总股本：{info_dict.get('总股本', 'N/A')}")
    print(f"  流通股：{info_dict.get('流通股', 'N/A')}")
except Exception as e:
    print(f"错误：{e}")

print("\n" + "="*60 + "\n")

# 方法 2: 东方财富实时行情（获取换手率、成交额等）
print("[2] 实时行情快照")
try:
    # 直接获取单只股票详情
    df_detail = ak.stock_individual_detail_em(symbol="002263")
    print(df_detail)
except Exception as e:
    print(f"错误：{e}")

print("\n" + "="*60 + "\n")

# 方法 3: 腾讯财经（快速获取核心数据）
print("[3] 腾讯财经快照")
try:
    import requests
    code = 'sz002263'
    url = f'http://qt.gtimg.cn/q={code}'
    resp = requests.get(url, timeout=5)
    resp.encoding = 'gbk'
    data = resp.text
    if '=' in data:
        parts = data.split('=')[1].strip('"').split('~')
        if len(parts) >= 50:
            print(f"  名称：{parts[1]}")
            print(f"  当前价：{parts[3]}")
            print(f"  成交量 (手): {parts[6]}")
            print(f"  成交额 (万): {parts[37] if len(parts) > 37 else 'N/A'}")
            print(f"  换手率 (%): {parts[42] if len(parts) > 42 else 'N/A'}")
            print(f"  总市值 (万): {parts[45] if len(parts) > 45 else 'N/A'}")
            print(f"  流通市值 (万): {parts[46] if len(parts) > 46 else 'N/A'}")
except Exception as e:
    print(f"错误：{e}")
