"""
QuantaAlpha 表达式解析器
支持横截面和时间序列函数，用于计算 ALPHA158 因子

参考：https://github.com/QuantaAlpha/QuantaAlpha
"""

import pandas as pd
import numpy as np
from typing import Optional, Union


# ===== 横截面函数 =====

def rank(series: pd.Series) -> pd.Series:
    """横截面排名 (0-1)"""
    return series.rank(pct=True)


def zscore(series: pd.Series) -> pd.Series:
    """横截面 Z 分数"""
    return (series - series.mean()) / series.std()


def cs_mean(series: pd.Series) -> float:
    """横截面均值"""
    return series.mean()


def cs_std(series: pd.Series) -> float:
    """横截面标准差"""
    return series.std()


def cs_max(series: pd.Series) -> float:
    """横截面最大值"""
    return series.max()


def cs_min(series: pd.Series) -> float:
    """横截面最小值"""
    return series.min()


def cs_median(series: pd.Series) -> float:
    """横截面中位数"""
    return series.median()


# ===== 时间序列函数 =====

def ref(series: pd.Series, n: int) -> pd.Series:
    """延迟 n 期"""
    return series.shift(n)


def delta(series: pd.Series, n: int) -> pd.Series:
    """n 期变化"""
    return series.diff(n)


def ts_mean(series: pd.Series, n: int) -> pd.Series:
    """n 期时间序列均值"""
    return series.rolling(window=n).mean()


def ts_sum(series: pd.Series, n: int) -> pd.Series:
    """n 期时间序列求和"""
    return series.rolling(window=n).sum()


def ts_std(series: pd.Series, n: int) -> pd.Series:
    """n 期时间序列标准差"""
    return series.rolling(window=n).std()


def ts_var(series: pd.Series, n: int) -> pd.Series:
    """n 期时间序列方差"""
    return series.rolling(window=n).var()


def ts_rank(series: pd.Series, n: int) -> pd.Series:
    """时间序列排名 (当前值在过去 n 期的排名)"""
    def _rank(x):
        if len(x) < n or pd.isna(x).any():
            return np.nan
        return (x.iloc[-1] > x.iloc[:-1]).sum() / (len(x) - 1)
    
    return series.rolling(window=n).apply(_rank, raw=False)


def ts_min(series: pd.Series, n: int) -> pd.Series:
    """n 期最小值"""
    return series.rolling(window=n).min()


def ts_max(series: pd.Series, n: int) -> pd.Series:
    """n 期最大值"""
    return series.rolling(window=n).max()


def ts_median(series: pd.Series, n: int) -> pd.Series:
    """n 期中位数"""
    return series.rolling(window=n).median()


def ts_pctchange(series: pd.Series, p: int) -> pd.Series:
    """p 期百分比变化"""
    return series.pct_change(periods=p)


def ts_argmax(series: pd.Series, n: int) -> pd.Series:
    """n 期内最大值的位置索引"""
    return series.rolling(window=n).apply(np.argmax, raw=True)


def ts_argmin(series: pd.Series, n: int) -> pd.Series:
    """n 期内最小值的位置索引"""
    return series.rolling(window=n).apply(np.argmin, raw=True)


def ts_corr(series_a: pd.Series, series_b: pd.Series, n: int) -> pd.Series:
    """n 期滚动相关系数"""
    return series_a.rolling(window=n).corr(series_b)


def ts_covariance(series_a: pd.Series, series_b: pd.Series, n: int) -> pd.Series:
    """n 期滚动协方差"""
    return series_a.rolling(window=n).cov(series_b)


# ===== 移动平均和 smoothing 函数 =====

def sma(series: pd.Series, n: int, m: int = 1) -> pd.Series:
    """简单移动平均 (兼容通达信 SMA)"""
    # 通达信 SMA: SMA(X,N,M) = (M*X + (N-M)*SMA(prev))/N
    result = series.copy()
    for i in range(len(series)):
        if i == 0:
            result.iloc[i] = series.iloc[i]
        else:
            result.iloc[i] = (m * series.iloc[i] + (n - m) * result.iloc[i-1]) / n
    return result


def wma(series: pd.Series, n: int) -> pd.Series:
    """加权移动平均"""
    weights = np.arange(1, n + 1)
    return series.rolling(window=n).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


def ema(series: pd.Series, n: int) -> pd.Series:
    """指数移动平均"""
    return series.ewm(span=n, adjust=False).mean()


def decaylinear(series: pd.Series, d: int) -> pd.Series:
    """线性加权移动平均"""
    weights = np.arange(1, d + 1)
    return series.rolling(window=d).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


# ===== 数学运算 =====

def prod(series: pd.Series, n: int) -> pd.Series:
    """n 期连乘"""
    return series.rolling(window=n).apply(lambda x: np.prod(x), raw=True)


def log_func(series: pd.Series) -> pd.Series:
    """自然对数"""
    return np.log(series)


def sqrt_func(series: pd.Series) -> pd.Series:
    """平方根"""
    return np.sqrt(series)


def pow_func(series: pd.Series, n: Union[int, float]) -> pd.Series:
    """n 次方"""
    return series ** n


def sign_func(series: pd.Series) -> pd.Series:
    """符号函数"""
    return np.sign(series)


def abs_func(series: pd.Series) -> pd.Series:
    """绝对值"""
    return np.abs(series)


def max_func(a: pd.Series, b: Union[pd.Series, float]) -> pd.Series:
    """逐元素最大值"""
    return np.maximum(a, b)


def min_func(a: pd.Series, b: Union[pd.Series, float]) -> pd.Series:
    """逐元素最小值"""
    return np.minimum(a, b)


def inv_func(series: pd.Series) -> pd.Series:
    """倒数"""
    return 1 / series


def floor_func(series: pd.Series) -> pd.Series:
    """向下取整"""
    return np.floor(series)


# ===== 条件逻辑函数 =====

def count(condition: pd.Series, n: int) -> pd.Series:
    """过去 n 期满足条件的次数"""
    return condition.astype(int).rolling(window=n).sum()


def sumif(series: pd.Series, n: int, condition: pd.Series) -> pd.Series:
    """过去 n 期满足条件的求和"""
    return (series * condition.astype(int)).rolling(window=n).sum()


def filter_func(series: pd.Series, condition: pd.Series) -> pd.Series:
    """条件过滤 (不满足条件的设为 NaN)"""
    return series.where(condition)


# ===== 技术指标 =====

def rsi(series: pd.Series, n: int) -> pd.Series:
    """RSI 相对强弱指标"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=n).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=n).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, short: int = 12, long: int = 26, signal: int = 9) -> tuple:
    """MACD 指标"""
    ema_short = series.ewm(span=short, adjust=False).mean()
    ema_long = series.ewm(span=long, adjust=False).mean()
    macd_line = ema_short - ema_long
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bb_middle(series: pd.Series, n: int) -> pd.Series:
    """布林带中轨"""
    return series.rolling(window=n).mean()


def bb_upper(series: pd.Series, n: int, std_dev: float = 2) -> pd.Series:
    """布林带上轨"""
    mid = bb_middle(series, n)
    std = series.rolling(window=n).std()
    return mid + std_dev * std


def bb_lower(series: pd.Series, n: int, std_dev: float = 2) -> pd.Series:
    """布林带下轨"""
    mid = bb_middle(series, n)
    std = series.rolling(window=n).std()
    return mid - std_dev * std


# ===== ALPHA158_20 因子实现 =====

def compute_alpha158_20(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算 ALPHA158_20 的 20 个精简因子
    
    Args:
        df: 包含 open, high, low, close, volume 的 DataFrame
    
    Returns:
        添加因子列的 DataFrame
    """
    # ROC 系列
    df['qa_roc0'] = (df['close'] - df['open']) / df['open']
    df['qa_roc1'] = df['close'] / ref(df['close'], 1) - 1
    df['qa_roc5'] = (df['close'] - ref(df['close'], 5)) / ref(df['close'], 5)
    df['qa_roc10'] = (df['close'] - ref(df['close'], 10)) / ref(df['close'], 10)
    df['qa_roc20'] = (df['close'] - ref(df['close'], 20)) / ref(df['close'], 20)
    
    # 成交量系列
    df['qa_vratio5'] = df['volume'] / ts_mean(df['volume'], 5)
    df['qa_vratio10'] = df['volume'] / ts_mean(df['volume'], 10)
    df['qa_vstd5_ratio'] = ts_std(df['volume'], 5) / ts_mean(df['volume'], 5)
    
    # 波动率系列
    df['qa_range'] = (df['high'] - df['low']) / df['open']
    df['qa_volatility5'] = ts_std(df['close'], 5) / df['close']
    df['qa_volatility10'] = ts_std(df['close'], 10) / df['close']
    
    # RSV 系列
    df['qa_rsv5'] = (df['close'] - ts_min(df['low'], 5)) / (ts_max(df['high'], 5) - ts_min(df['low'], 5) + 1e-12)
    df['qa_rsv10'] = (df['close'] - ts_min(df['low'], 10)) / (ts_max(df['high'], 10) - ts_min(df['low'], 10) + 1e-12)
    
    # K 线形态
    df['qa_high_ratio5'] = df['close'] / ts_max(df['high'], 5) - 1
    df['qa_low_ratio5'] = df['close'] / ts_min(df['low'], 5) - 1
    df['qa_shadow_ratio'] = (df['high'] - df['close']) / (df['close'] - df['low'] + 1e-12)
    df['qa_body_ratio'] = (df['close'] - df['open']) / (df['high'] - df['low'] + 1e-12)
    
    # 均线比率
    df['qa_ma_ratio5_10'] = ts_mean(df['close'], 5) / ts_mean(df['close'], 10) - 1
    df['qa_ma_ratio10_20'] = ts_mean(df['close'], 10) / ts_mean(df['close'], 20) - 1
    
    return df


# ===== 表达式解析器 =====

class QAExpressionParser:
    """
    QuantaAlpha 表达式解析器
    
    支持将 QuantaAlpha 风格的因子表达式转换为 Python 代码并计算
    """
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._setup_namespace()
    
    def _setup_namespace(self):
        """设置命名空间"""
        self.namespace = {
            # 数据列
            'open': self.df['open'],
            'high': self.df['high'],
            'low': self.df['low'],
            'close': self.df['close'],
            'volume': self.df['volume'],
            
            # 函数
            'Ref': ref,
            'Delta': delta,
            'Mean': ts_mean,
            'Sum': ts_sum,
            'Std': ts_std,
            'Var': ts_var,
            'Min': ts_min,
            'Max': ts_max,
            'Median': ts_median,
            'Rank': ts_rank,
            'PctChange': ts_pctchange,
            'ArgMax': ts_argmax,
            'ArgMin': ts_argmin,
            'Corr': ts_corr,
            'Covariance': ts_covariance,
            
            'SMA': sma,
            'WMA': wma,
            'EMA': ema,
            'DecayLinear': decaylinear,
            
            'Prod': prod,
            'Log': log_func,
            'Sqrt': sqrt_func,
            'Pow': pow_func,
            'Sign': sign_func,
            'Abs': abs_func,
            'Max': max_func,
            'Min': min_func,
            'Inv': inv_func,
            'Floor': floor_func,
            
            'Count': count,
            'SumIf': sumif,
            'Filter': filter_func,
            
            'RSI': rsi,
            'MACD': macd,
            'BB_MIDDLE': bb_middle,
            'BB_UPPER': bb_upper,
            'BB_LOWER': bb_lower,
            
            # 横截面函数
            'RANK': rank,
            'ZSCORE': zscore,
            'MEAN': cs_mean,
            'STD': cs_std,
            'MAX': cs_max,
            'MIN': cs_min,
            'MEDIAN': cs_median,
            
            # numpy
            'np': np,
            'pd': pd,
        }
    
    def parse(self, expr: str) -> pd.Series:
        """
        解析并计算表达式
        
        Args:
            expr: QuantaAlpha 风格的表达式，如 "($close-Ref($close, 5))/Ref($close, 5)"
        
        Returns:
            计算结果 Series
        """
        # 替换 $close -> close, $volume -> volume
        python_expr = expr
        for col in ['close', 'open', 'high', 'low', 'volume', 'vwap']:
            python_expr = python_expr.replace(f'${col}', col)
        
        # 安全计算
        try:
            result = eval(python_expr, {"__builtins__": {}}, self.namespace)
            return result
        except Exception as e:
            print(f"表达式解析错误：{expr}")
            print(f"错误信息：{e}")
            return pd.Series(np.nan, index=self.df.index)


def compute_factor(df: pd.DataFrame, expr: str, factor_name: str = None) -> pd.DataFrame:
    """
    计算单个因子
    
    Args:
        df: 原始数据
        expr: QuantaAlpha 表达式
        factor_name: 因子名称
    
    Returns:
        添加因子列的 DataFrame
    """
    parser = QAExpressionParser(df)
    result = parser.parse(expr)
    
    if factor_name:
        df[factor_name] = result
    else:
        df['factor'] = result
    
    return df


def compute_factors(df: pd.DataFrame, factors: dict) -> pd.DataFrame:
    """
    批量计算因子
    
    Args:
        df: 原始数据
        factors: {因子名：表达式} 字典
    
    Returns:
        添加因子列的 DataFrame
    """
    for factor_name, expr in factors.items():
        df = compute_factor(df, expr, f'qa_{factor_name.lower()}')
    
    return df


# ===== 使用示例 =====

if __name__ == "__main__":
    # 测试数据
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    test_df = pd.DataFrame({
        'open': 100 + np.cumsum(np.random.randn(100)),
        'high': 100 + np.cumsum(np.random.randn(100)) + np.abs(np.random.randn(100)),
        'low': 100 + np.cumsum(np.random.randn(100)) - np.abs(np.random.randn(100)),
        'close': 100 + np.cumsum(np.random.randn(100)),
        'volume': 1000000 + np.random.randn(100) * 100000,
    }, index=dates)
    
    # 计算 ALPHA158_20 因子
    result_df = compute_alpha158_20(test_df.copy())
    
    print("ALPHA158_20 因子计算结果:")
    print(result_df.tail())
    print(f"\n因子列：{[c for c in result_df.columns if c.startswith('qa_')]}")
    
    # 测试表达式解析器
    parser = QAExpressionParser(test_df.copy())
    roc5 = parser.parse("($close-Ref($close, 5))/Ref($close, 5)")
    print(f"\nROC5 (解析器): {roc5.tail().values}")
    print(f"ROC5 (直接计算): {result_df['qa_roc5'].tail().values}")
