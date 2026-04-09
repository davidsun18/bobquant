# -*- coding: utf-8 -*-
"""
BobQuant ML 特征工程 v2.1 - 集成三重障碍法

功能:
1. 三重障碍法标签生成 (mlfinlab 核心算法)
2. 分数阶差分特征处理
3. 动态止盈止损调整

使用方式:
    from bobquant.ml.features import generate_features_with_triple_barrier
    df = generate_features_with_triple_barrier(stock_data)
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional
from pathlib import Path


def apply_triple_barrier(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    events: pd.DataFrame,
    pt_sl: Tuple[float, float] = (1.0, 1.0),
    t1: pd.Timedelta = pd.Timedelta('5D'),
    min_ret: float = 0.02
) -> pd.Series:
    """
    三重障碍法标签生成 - mlfinlab 核心算法
    
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


def generate_features_with_triple_barrier(
    df: pd.DataFrame,
    pt_sl: Tuple[float, float] = (1.0, 1.0),
    t1_days: int = 5,
    min_ret: float = 0.02,
    fracdiff_d: float = 0.4
) -> pd.DataFrame:
    """
    生成 ML 特征，使用三重障碍法标签
    
    参数:
        df: OHLCV 数据，需包含 date, open, high, low, close, volume 列
        pt_sl: (止盈倍数，止损倍数)
        t1_days: 时间窗口（天数）
        min_ret: 最小预期收益率
        fracdiff_d: 分数阶差分阶数
    
    返回:
        包含特征和标签的 DataFrame
    """
    # 确保索引为日期
    if 'date' in df.columns:
        df = df.set_index('date')
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    
    # 生成事件（每日开盘）
    events = df[['close']].copy()
    
    # 应用三重障碍法
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
    df['close_fracdiff'] = fractional_differentiation(df['close'], d=fracdiff_d)
    
    # 添加标签
    df['label'] = labels
    
    # 计算传统特征
    df['returns'] = df['close'].pct_change()
    df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
    df['volatility'] = df['returns'].rolling(20).std()
    df['momentum_5d'] = df['close'] / df['close'].shift(5) - 1
    df['momentum_10d'] = df['close'] / df['close'].shift(10) - 1
    
    # 标签统计
    label_counts = df['label'].value_counts().sort_index()
    
    return df, {
        'total_samples': len(df),
        'label_distribution': {
            '-1 (stop_loss)': int(label_counts.get(-1, 0)),
            '0 (neutral)': int(label_counts.get(0, 0)),
            '+1 (take_profit)': int(label_counts.get(1, 0))
        },
        'params': {
            'pt_sl': pt_sl,
            't1_days': t1_days,
            'min_ret': min_ret,
            'fracdiff_d': fracdiff_d
        }
    }


def compare_labeling_methods(
    df: pd.DataFrame,
    traditional_window: int = 5
) -> dict:
    """
    比较传统标签方法和三重障碍法
    
    参数:
        df: OHLCV 数据
        traditional_window: 传统方法的时间窗口（天数）
    
    返回:
        对比统计结果
    """
    df_indexed = df.copy()
    if 'date' in df_indexed.columns:
        df_indexed = df_indexed.set_index('date')
    df_indexed.index = pd.to_datetime(df_indexed.index)
    
    # 传统方法：N 日后涨跌
    traditional_label = (df_indexed['close'].shift(-traditional_window) > df_indexed['close']).astype('int8')
    traditional_label[df_indexed['close'].shift(-traditional_window) < df_indexed['close']] = -1
    traditional_label.name = 'traditional_label'
    
    # 三重障碍法
    events = df_indexed[['close']].copy()
    tb_label = apply_triple_barrier(
        close=df_indexed['close'],
        high=df_indexed['high'],
        low=df_indexed['low'],
        events=events,
        pt_sl=(1.0, 1.0),
        t1=pd.Timedelta(f'{traditional_window}D'),
        min_ret=0.02
    )
    
    # 统计对比
    tb_counts = tb_label.value_counts().sort_index()
    trad_counts = traditional_label.value_counts().sort_index()
    
    return {
        'traditional': {
            'method': f'{traditional_window}日固定窗口',
            'distribution': {
                '-1': int(trad_counts.get(-1, 0)),
                '0': int(trad_counts.get(0, 0)),
                '+1': int(trad_counts.get(1, 0))
            },
            'balance': trad_counts.get(1, 0) / max(trad_counts.get(-1, 1), 1)
        },
        'triple_barrier': {
            'method': '三重障碍法',
            'distribution': {
                '-1': int(tb_counts.get(-1, 0)),
                '0': int(tb_counts.get(0, 0)),
                '+1': int(tb_counts.get(1, 0))
            },
            'balance': tb_counts.get(1, 0) / max(tb_counts.get(-1, 1), 1)
        }
    }


# 使用示例
if __name__ == '__main__':
    # 测试数据
    test_df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=100, freq='D'),
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 102,
        'low': np.random.randn(100).cumsum() + 98,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    # 生成特征
    df_features, stats = generate_features_with_triple_barrier(test_df)
    
    print("📊 三重障碍法标签生成测试")
    print("=" * 50)
    print(f"总样本数：{stats['total_samples']}")
    print(f"标签分布:")
    for label, count in stats['label_distribution'].items():
        pct = count / stats['total_samples'] * 100
        print(f"  {label}: {count} ({pct:.1f}%)")
    print(f"\n参数设置:")
    for key, value in stats['params'].items():
        print(f"  {key}: {value}")
    
    # 对比传统方法
    print("\n" + "=" * 50)
    print("📈 标签方法对比")
    comparison = compare_labeling_methods(test_df)
    print(f"\n传统方法 ({comparison['traditional']['method']}):")
    print(f"  分布：{comparison['traditional']['distribution']}")
    print(f"  平衡性：{comparison['traditional']['balance']:.2f}")
    
    print(f"\n三重障碍法 ({comparison['triple_barrier']['method']}):")
    print(f"  分布：{comparison['triple_barrier']['distribution']}")
    print(f"  平衡性：{comparison['triple_barrier']['balance']:.2f}")
