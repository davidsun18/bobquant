#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三重障碍法标签生成器 - mlfinlab 核心算法实现

功能:
- 三重障碍法标签生成 (Triple Barrier Method)
- 分数阶差分特征处理
- 动态止盈止损调整

使用示例:
    python triple_barrier_labeling.py --input data/000001.SZ.csv --output labeled_data.csv
"""

import argparse
import numpy as np
import pandas as pd
from typing import Tuple, Optional
from pathlib import Path


def apply_triple_barrier(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    events: pd.DataFrame,
    pt_sl: Tuple[float, float] = (1.0, 1.0),
    t1: pd.Timedelta = pd.Timedelta('10D'),
    min_ret: float = 0.005
) -> pd.Series:
    """
    三重障碍法标签生成
    
    原理:
    传统 ML 标签使用固定时间窗口（如"明天涨/跌"），但忽略了：
    - 价格可能先触及止损再反弹
    - 不同波动率下应使用不同的止盈/止损距离
    - 时间衰减因素
    
    三重障碍法定义三个退出边界：
    1. 上障碍：入场价 × (1 + 动态止盈率)
    2. 下障碍：入场价 × (1 - 动态止损率)
    3. 右障碍：固定时间窗口
    
    标签根据价格先触及哪个障碍决定：
    - 先触上障碍 → +1 (做多盈利)
    - 先触下障碍 → -1 (做多亏损)
    - 先触右障碍 → 0 (持有到期，按最终价格判断)
    
    参数:
        close: 收盘价序列
        high: 最高价序列
        low: 最低价序列
        events: 事件 DataFrame，索引为入场时间，包含'close'列（入场价）
        pt_sl: (止盈倍数，止损倍数)，相对于 min_ret
        t1: 时间窗口
        min_ret: 最小预期收益率
    
    返回:
        labels: 标签序列 (+1, -1, 0)
    """
    labels = pd.Series(index=events.index, dtype='int8', name='label')
    
    for t0 in events.index:
        # 计算动态障碍
        pt = pt_sl[0] * min_ret  # 止盈阈值
        sl = pt_sl[1] * min_ret  # 止损阈值
        
        upper_barrier = events.loc[t0, 'close'] * (1 + pt)
        lower_barrier = events.loc[t0, 'close'] * (1 - sl)
        
        # 获取时间窗口内的价格路径
        t1_time = t0 + t1
        if t1_time > close.index[-1]:
            t1_time = close.index[-1]
        
        # 确保时间范围有效
        mask = (close.index >= t0) & (close.index <= t1_time)
        if not mask.any():
            labels.loc[t0] = 0
            continue
        
        path = close.loc[mask]
        path_high = high.loc[mask]
        path_low = low.loc[mask]
        
        if len(path) == 0:
            labels.loc[t0] = 0
            continue
        
        # 检查是否触及障碍
        hit_upper = path_high[path_high >= upper_barrier]
        hit_lower = path_low[path_low <= lower_barrier]
        
        # 确定退出时间
        if len(hit_upper) == 0 and len(hit_lower) == 0:
            # 未触及任何障碍，持有到期
            exit_price = path.iloc[-1]
            ret = (exit_price - events.loc[t0, 'close']) / events.loc[t0, 'close']
            labels.loc[t0] = 1 if ret > 0 else -1 if ret < 0 else 0
        elif len(hit_upper) > 0 and (len(hit_lower) == 0 or hit_upper.index[0] <= hit_lower.index[0]):
            # 先触及上障碍
            labels.loc[t0] = 1
        else:
            # 先触及下障碍
            labels.loc[t0] = -1
    
    return labels


def fractional_differentiation(
    price: pd.Series,
    d: float = 0.4,
    threshold: float = 1e-5
) -> pd.Series:
    """
    分数阶差分 - 在平稳性和记忆性之间取得平衡
    
    传统差分 (d=1) 会完全消除记忆性，而分数阶差分可以：
    - 保留更多历史记忆 (d 越小保留越多)
    - 实现序列平稳化
    - 适合金融时间序列特征工程
    
    参数:
        price: 价格序列
        d: 差分阶数 (0<d<1)，越小保留越多记忆
        threshold: 权重截断阈值
    
    返回:
        分数阶差分后的序列
    """
    # 计算分数阶差分的权重
    # 使用二项式系数展开：(1-L)^d = 1 - dL + d(d-1)/2! L^2 - ...
    weights = [1.0]
    for k in range(1, len(price)):
        weight = -weights[-1] * (d - k + 1) / k
        if abs(weight) < threshold:
            break
        weights.append(weight)
    
    # 应用权重
    result = pd.Series(index=price.index, dtype='float64', name=f'fracdiff_{d}')
    
    # 使用滚动窗口应用权重
    for i in range(len(weights), len(price)):
        result.iloc[i] = np.dot(weights, price.iloc[i-len(weights):i+1].values[::-1])
    
    return result


def calculate_dynamic_min_ret(
    close: pd.Series,
    window: int = 20,
    multiplier: float = 1.0
) -> pd.Series:
    """
    基于波动率计算动态最小预期收益率
    
    高波动股票应使用更大的止盈/止损阈值
    
    参数:
        close: 收盘价序列
        window: 滚动窗口大小
        multiplier: 调整倍数
    
    返回:
        动态 min_ret 序列
    """
    # 使用对数收益率的滚动标准差作为波动率估计
    log_ret = np.log(close / close.shift(1))
    volatility = log_ret.rolling(window=window).std()
    
    # 转换为预期收益率（假设持有 N 天）
    min_ret = volatility * multiplier
    
    return min_ret


def generate_events(
    df: pd.DataFrame,
    method: str = 'daily',
    threshold: float = 0.0
) -> pd.DataFrame:
    """
    生成交易事件
    
    参数:
        df: OHLC 数据
        method: 事件生成方法
            - 'daily': 每日开盘
            - 'threshold': 价格变动超过阈值
        threshold: 价格变动阈值（仅 threshold 方法使用）
    
    返回:
        events DataFrame，索引为事件时间，包含'close'列
    """
    if method == 'daily':
        # 每日开盘作为事件
        events = df[['close']].copy()
    
    elif method == 'threshold':
        # 价格变动超过阈值时生成事件
        returns = df['close'].pct_change()
        event_mask = returns.abs() > threshold
        events = df.loc[event_mask, ['close']].copy()
    
    else:
        raise ValueError(f"未知的事件生成方法：{method}")
    
    return events


def process_file(
    input_path: str,
    output_path: str,
    pt_sl: Tuple[float, float] = (1.0, 1.0),
    t1_days: int = 5,
    min_ret: float = 0.02,
    fracdiff_d: float = 0.4
):
    """
    处理 CSV 文件，生成带标签的数据
    
    参数:
        input_path: 输入 CSV 文件路径（需包含 date, open, high, low, close 列）
        output_path: 输出 CSV 文件路径
        pt_sl: (止盈倍数，止损倍数)
        t1_days: 时间窗口（天数）
        min_ret: 最小预期收益率
        fracdiff_d: 分数阶差分阶数
    """
    print(f"📖 读取数据：{input_path}")
    df = pd.read_csv(input_path, parse_dates=['date'], index_col='date')
    
    # 确保索引按时间排序
    df = df.sort_index()
    
    print(f"📊 数据形状：{df.shape}")
    print(f"📅 时间范围：{df.index.min()} 至 {df.index.max()}")
    
    # 生成事件（每日开盘）
    events = generate_events(df, method='daily')
    print(f"📌 生成事件数：{len(events)}")
    
    # 应用三重障碍法
    print(f"🎯 应用三重障碍法 (pt_sl={pt_sl}, t1={t1_days}天，min_ret={min_ret})...")
    labels = apply_triple_barrier(
        close=df['close'],
        high=df['high'],
        low=df['low'],
        events=events,
        pt_sl=pt_sl,
        t1=pd.Timedelta(f'{t1_days}D'),
        min_ret=min_ret
    )
    
    # 分数阶差分特征
    print(f"🔢 计算分数阶差分 (d={fracdiff_d})...")
    df['close_fracdiff'] = fractional_differentiation(df['close'], d=fracdiff_d)
    
    # 添加标签到数据
    df['label'] = labels
    
    # 计算标签分布
    label_counts = df['label'].value_counts().sort_index()
    print(f"\n📊 标签分布:")
    print(f"  -1 (止损): {label_counts.get(-1, 0):6d} ({label_counts.get(-1, 0)/len(df)*100:.1f}%)")
    print(f"   0 (中性): {label_counts.get(0, 0):6d} ({label_counts.get(0, 0)/len(df)*100:.1f}%)")
    print(f"  +1 (止盈): {label_counts.get(1, 0):6d} ({label_counts.get(1, 0)/len(df)*100:.1f}%)")
    
    # 保存结果
    print(f"\n💾 保存结果：{output_path}")
    df.to_csv(output_path)
    
    print("✅ 处理完成!")


def main():
    parser = argparse.ArgumentParser(
        description='三重障碍法标签生成器 - mlfinlab 核心算法',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 默认参数处理
  python triple_barrier_labeling.py --input data/000001.SZ.csv --output labeled_data.csv
  
  # 自定义参数
  python triple_barrier_labeling.py -i data/000001.SZ.csv -o labeled.csv --pt_sl 1.5 1.0 --t1 10 --min_ret 0.03
        """
    )
    
    parser.add_argument('-i', '--input', required=True, help='输入 CSV 文件路径')
    parser.add_argument('-o', '--output', required=True, help='输出 CSV 文件路径')
    parser.add_argument('--pt_sl', nargs=2, type=float, default=[1.0, 1.0],
                       help='止盈倍数和止损倍数 (默认：1.0 1.0)')
    parser.add_argument('--t1', type=int, default=5, help='时间窗口天数 (默认：5)')
    parser.add_argument('--min_ret', type=float, default=0.02, help='最小预期收益率 (默认：0.02)')
    parser.add_argument('--fracdiff_d', type=float, default=0.4, help='分数阶差分阶数 (默认：0.4)')
    
    args = parser.parse_args()
    
    process_file(
        input_path=args.input,
        output_path=args.output,
        pt_sl=tuple(args.pt_sl),
        t1_days=args.t1,
        min_ret=args.min_ret,
        fracdiff_d=args.fracdiff_d
    )


if __name__ == '__main__':
    main()
