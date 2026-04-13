#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')
from bobquant.data.provider import get_provider

provider = get_provider('tencent')

# 获取大东南的历史 K 线数据（最近 30 天）
df = provider.get_history('sz.002263', days=30)

print('=== 大东南 (sz.002263) K 线数据 ===')
print('数据源：Baostock')
print()
if df is not None:
    # 显示最近 10 个交易日
    print('日期        开盘     最高     最低     收盘     成交量 (万手)')
    print('-' * 60)
    for date, row in df.tail(10).iterrows():
        vol = int(row['volume']) / 100
        print(f'{str(date)[:10]}  {row["open"]:.2f}   {row["high"]:.2f}   {row["low"]:.2f}   {row["close"]:.2f}   {vol:.2f}')
    print()
    print(f'总记录数：{len(df)} 条')
else:
    print('获取失败')
