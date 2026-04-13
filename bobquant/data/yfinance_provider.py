# -*- coding: utf-8 -*-
"""
BobQuant yfinance 数据源
支持美股、港股、A 股数据获取

注意：yfinance 有严格的速率限制，建议：
1. 设置 delay >= 2 秒避免被限制
2. 批量获取时控制并发
3. 生产环境建议使用付费 API 或缓存

使用示例:
    from data.provider import get_provider
    
    # 使用 yfinance 数据源 (推荐 delay=2-3 秒)
    provider = get_provider('yfinance', retry=3, delay=2.0)
    
    # 获取实时行情
    quote = provider.get_quote('AAPL')
    
    # 获取历史数据
    df = provider.get_history('AAPL', days=60)
    
    # 批量获取
    quotes = provider.get_quotes(['AAPL', 'MSFT', 'GOOGL'])
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
from .provider import DataProvider


class YFinanceProvider(DataProvider):
    """yfinance 数据源 (支持美股、港股、A 股)"""

    def __init__(self, retry=3, timeout=30, delay=2.0):
        """
        初始化 yfinance 数据源
        
        Args:
            retry: 重试次数
            timeout: 请求超时时间 (秒)
            delay: 请求间隔时间 (秒)，建议 >= 2 秒避免速率限制
        """
        self.retry = retry
        self.timeout = timeout
        self.delay = delay
        # 关闭 yfinance 调试日志
        yf.config.debug_logging = False

    def _get_yf_symbol(self, code: str) -> str:
        """
        将股票代码转换为 yfinance 格式
        
        Args:
            code: 原始股票代码 (如 sh600519, sz000001, hk00700, AAPL)
            
        Returns:
            yfinance 格式的代码
        """
        code = code.lower().strip()
        
        # A 股：sh600519 -> 600519.SS, sz000001 -> 000001.SZ
        if code.startswith('sh'):
            return f"{code[2:]}.SS"
        elif code.startswith('sz'):
            return f"{code[2:]}.SZ"
        # 港股：hk00700 -> 0700.HK
        elif code.startswith('hk'):
            return f"{code[2:]}.HK"
        # 美股：直接返回 (AAPL, GOOGL 等)
        else:
            return code.upper()

    def get_quote(self, code: str) -> Optional[Dict]:
        """
        获取实时行情
        
        Args:
            code: 股票代码
            
        Returns:
            dict: {name, current, open, pre_close, high, low, change, volume}
        """
        for i in range(self.retry):
            try:
                symbol = self._get_yf_symbol(code)
                ticker = yf.Ticker(symbol)
                
                # 获取最新价格 - 使用 history 更可靠
                hist = ticker.history(period='1d', timeout=self.timeout)
                
                if hist.empty:
                    if i < self.retry - 1:
                        wait_time = self.delay * (i + 1)
                        time.sleep(wait_time)
                        continue
                    return None
                
                # 从历史数据中获取
                latest = hist.iloc[-1]
                current = float(latest['Close'])
                open_price = float(latest['Open'])
                high = float(latest['High'])
                low = float(latest['Low'])
                volume = float(latest['Volume']) if 'Volume' in latest else 0
                
                # 获取昨收 (需要获取前一天的数据)
                hist_2d = ticker.history(period='2d', timeout=self.timeout)
                if len(hist_2d) >= 2:
                    pre_close = float(hist_2d.iloc[-2]['Close'])
                else:
                    pre_close = current
                
                # 计算涨跌幅
                change = ((current - pre_close) / pre_close * 100) if pre_close > 0 else 0
                
                # 获取股票名称
                try:
                    info = ticker.info
                    name = info.get('shortName', info.get('longName', code))
                except:
                    name = code
                
                return {
                    'name': name,
                    'current': current,
                    'open': open_price,
                    'pre_close': pre_close,
                    'high': high,
                    'low': low,
                    'change': change,
                    'volume': volume,
                }
            except Exception as e:
                print(f"[yfinance 错误] {code}: {e}")
                if i < self.retry - 1:
                    wait_time = self.delay * (i + 1)
                    time.sleep(wait_time)  # 递增延迟
        
        return None

    def get_history(self, code: str, days: int = 60) -> Optional[pd.DataFrame]:
        """
        获取历史 K 线
        
        Args:
            code: 股票代码
            days: 获取天数
            
        Returns:
            DataFrame: date, open, high, low, close, volume
        """
        try:
            symbol = self._get_yf_symbol(code)
            ticker = yf.Ticker(symbol)
            
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 获取历史数据
            hist = ticker.history(start=start_date, end=end_date, interval='1d', timeout=self.timeout)
            
            if hist.empty:
                return None
            
            # 重命名列以匹配接口
            df = hist.copy()
            df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            }, inplace=True)
            
            # 选择需要的列
            columns_to_keep = ['open', 'high', 'low', 'close', 'volume']
            df = df[[col for col in columns_to_keep if col in df.columns]]
            
            # 转换类型
            df = df.astype({
                'open': float, 'high': float, 'low': float,
                'close': float, 'volume': float
            })
            
            return df
            
        except Exception as e:
            print(f"[yfinance 历史数据错误] {code}: {e}")
            return None

    def get_quotes(self, codes: List[str]) -> Dict[str, dict]:
        """
        批量获取多只股票行情
        
        Args:
            codes: 股票代码列表
            
        Returns:
            dict: {code: quote} 行情字典
        """
        results = {}
        for i, code in enumerate(codes):
            quote = self.get_quote(code)
            if quote:
                results[code] = quote
            # 添加延迟避免速率限制
            if i < len(codes) - 1:
                time.sleep(self.delay)
        return results


# 测试函数
def test_yfinance_provider():
    """测试 yfinance 数据源"""
    print("=" * 60)
    print("yfinance 数据源测试")
    print("=" * 60)
    
    provider = YFinanceProvider()
    
    # 测试股票列表 (美股、港股、A 股)
    test_stocks = [
        ('AAPL', '美股 - 苹果'),
        ('GOOGL', '美股 - 谷歌'),
        ('hk00700', '港股 - 腾讯'),
        ('sh600519', 'A 股 - 茅台'),
        ('sz000001', 'A 股 - 平安银行'),
    ]
    
    print("\n1. 测试实时行情获取 (get_quote)")
    print("-" * 60)
    for code, desc in test_stocks:
        print(f"\n获取 {desc} ({code})...")
        quote = provider.get_quote(code)
        if quote:
            print(f"  ✓ 名称：{quote['name']}")
            print(f"  ✓ 当前价：{quote['current']:.2f}")
            print(f"  ✓ 开盘价：{quote['open']:.2f}")
            print(f"  ✓ 昨收：{quote['pre_close']:.2f}")
            print(f"  ✓ 涨跌幅：{quote['change']:.2f}%")
            print(f"  ✓ 成交量：{quote['volume']:,.0f}")
        else:
            print(f"  ✗ 获取失败")
    
    print("\n\n2. 测试历史数据获取 (get_history)")
    print("-" * 60)
    for code, desc in test_stocks[:3]:  # 只测试前 3 个
        print(f"\n获取 {desc} ({code}) 历史数据 (60 天)...")
        df = provider.get_history(code, days=60)
        if df is not None and not df.empty:
            print(f"  ✓ 获取成功，共 {len(df)} 条记录")
            print(f"  ✓ 日期范围：{df.index[0].strftime('%Y-%m-%d')} 至 {df.index[-1].strftime('%Y-%m-%d')}")
            print(f"  ✓ 最新收盘价：{df['close'].iloc[-1]:.2f}")
        else:
            print(f"  ✗ 获取失败")
    
    print("\n\n3. 测试批量获取 (get_quotes)")
    print("-" * 60)
    codes = ['AAPL', 'GOOGL', 'MSFT']
    print(f"批量获取美股：{', '.join(codes)}")
    quotes = provider.get_quotes(codes)
    for code, quote in quotes.items():
        if quote:
            print(f"  ✓ {code}: {quote['current']:.2f} ({quote['change']:+.2f}%)")
        else:
            print(f"  ✗ {code}: 获取失败")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_yfinance_provider()
