# BobQuant 股票实时数据 API 配置文档

**版本**: v2.5  
**更新时间**: 2026-04-10  

---

## 📡 数据源配置

### 主数据源：腾讯财经

**配置**:
```yaml
data:
  primary: "tencent"
  fallback: "tencent"
  history_provider: "baostock"
  realtime_refresh: 2  # 2 秒刷新一次
```

### API 接口

#### 1. 实时行情 API（腾讯财经）

**接口地址**:
```
http://qt.gtimg.cn/q={symbol}
```

**参数**:
- `symbol`: 股票代码（去掉点和后缀）
  - 上交所：`sh600519` → `600519`
  - 深交所：`sz000001` → `000001`

**示例**:
```bash
# 贵州茅台
curl "http://qt.gtimg.cn/q=600519"

# 平安银行
curl "http://qt.gtimg.cn/q=000001"
```

**返回格式** (GBK 编码):
```
v_sh600519="51~贵州茅台~600519~1500.00~1495.00~1505.00~...~33~1510.00~34~1490.00~..."
```

**字段解析** (Python):
```python
import requests

def get_quote(code):
    """获取实时行情"""
    symbol = code.replace('.', '')  # sh.600519 → 600519
    url = f"http://qt.gtimg.cn/q={symbol}"
    
    headers = {
        'Referer': 'http://stockapp.finance.qq.com',
        'User-Agent': 'Mozilla/5.0'
    }
    
    resp = requests.get(url, headers=headers, timeout=3)
    resp.encoding = 'gbk'
    
    data = resp.text.strip()
    if '=' in data and '"' in data:
        parts = data.split('=')[1].strip('"').split('~')
        
        if len(parts) >= 32:
            return {
                'name': parts[1],           # 股票名称
                'current': float(parts[3]),  # 当前价
                'open': float(parts[5]),     # 开盘价
                'pre_close': float(parts[4]), # 昨收
                'high': float(parts[33]),    # 最高价
                'low': float(parts[34]),     # 最低价
                'volume': float(parts[6]),   # 成交量
            }
    return None
```

**字段说明**:
| 索引 | 字段 | 说明 |
|------|------|------|
| 1 | name | 股票名称 |
| 3 | current | 当前价 |
| 4 | pre_close | 昨收价 |
| 5 | open | 开盘价 |
| 6 | volume | 成交量（手） |
| 33 | high | 最高价 |
| 34 | low | 最低价 |

---

#### 2. 历史 K 线 API（Baostock）

**安装**:
```bash
pip3 install baostock
```

**使用示例**:
```python
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta

def get_history(code, days=60):
    """获取历史 K 线"""
    lg = bs.login()
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    rs = bs.query_history_k_data_plus(
        code, 
        "date,open,high,low,close,volume",
        start_date=start_date, 
        end_date=end_date, 
        frequency="d"
    )
    
    data_list = []
    while rs.error_code == '0' and rs.next():
        data_list.append(rs.get_row_data())
    
    df = pd.DataFrame(data_list, columns=rs.fields)
    df.index = pd.to_datetime(df['date'])
    
    bs.logout()
    return df
```

**返回字段**:
- `date`: 日期
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `volume`: 成交量

---

## 🚀 并行刷新优化

**v1.1 优化**: 使用 ThreadPoolExecutor 并行刷新多只股票

```python
from concurrent.futures import ThreadPoolExecutor

class TencentProvider:
    def __init__(self, max_workers=10):
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def get_quotes(self, codes: List[str]) -> Dict[str, dict]:
        """并行获取多只股票行情"""
        futures = {
            self._executor.submit(self.get_quote, code): code 
            for code in codes
        }
        
        results = {}
        for future in as_completed(futures):
            code = futures[future]
            quote = future.result()
            if quote:
                results[code] = quote
        
        return results
```

**性能对比**:
- **串行**: 26 只股票 × 0.1 秒 = 2.6 秒
- **并行**: 26 只股票 / 10 线程 = 0.3 秒 ⚡

---

## 📋 配置文件模板

**sim_config.yaml**:
```yaml
# --- 数据源 ---
data:
  primary: "tencent"                # 腾讯财经（实时）
  fallback: "tencent"               # 备用数据源
  history_provider: "baostock"      # 历史数据
  history_days: 120                 # 历史数据天数
  realtime_refresh: 2               # 实时刷新间隔（秒）
  max_workers: 10                   # 并行线程数
```

---

## 🔧 其他数据源（备选）

### 新浪财经
```python
url = f"http://hq.sinajs.cn/list={symbol}"
# symbol: sh600519, sz000001
```

### 网易财经
```python
url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen=100"
```

### 阿里云 API 市场
```python
url = "https://stockapi.market.alicloudapi.com/stock/realtime"
headers = {'Authorization': 'APPKEY xxx'}
```

---

## ⚠️ 注意事项

1. **腾讯财经**:
   - 免费，无需 API Key
   - 支持 A 股、港股、美股
   - 交易时段实时更新
   - 限流：单 IP ≤ 100 次/分钟

2. **Baostock**:
   - 免费，需登录
   - 盘后更新（20:00 后）
   - 适合历史数据回测

3. **并发限制**:
   - 建议 `max_workers ≤ 10`
   - 避免被封 IP

---

## 📞 联系支持

**文档**: `/home/openclaw/.openclaw/workspace/quant_strategies/docs/data_api.md`  
**代码**: `bobquant/data/provider.py`

**配置完成后可直接使用**:
```python
from bobquant.data.provider import get_provider

data = get_provider('tencent')
quote = data.get_quote('sh.600519')
history = data.get_history('sh.600519', days=60)
```

---

*最后更新：2026-04-10*
