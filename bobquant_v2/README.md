# BobQuant V2 - 简洁量化交易框架

## 设计原则

1. **单一职责**：每个模块只做一件事
2. **接口统一**：相同功能使用统一接口
3. **可复用**：组件化设计，方便迭代
4. **简洁**：去除冗余，核心代码 < 2000 行

## 架构

```
bobquant_v2/
├── api/              # 数据接口层（统一数据访问）
│   ├── base_api.py   # API基类（缓存、工具）
│   ├── account_api.py
│   ├── trade_api.py
│   └── market_api.py
├── web/              # Web服务层
│   ├── app.py        # Flask应用（统一API）
│   └── templates/
│       └── index.html
└── __init__.py
```

## 对比V1

| 项目 | V1 | V2 |
|------|-----|-----|
| 代码行数 | 8753行 | ~1500行 |
| 文件数 | 44个 | 8个 |
| 目录层级 | 5层 | 2层 |
| 接口统一 | 否 | ✅ 是 |
| 缓存机制 | 分散 | ✅ 统一 |
| 数据格式 | 不一致 | ✅ 标准化 |

## 快速开始

### 1. 启动API服务

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
python3 bobquant_v2/web/app.py
```

### 2. 访问Web界面

```
http://localhost:5000
```

### 3. API接口

```
GET /api/account          # 账户数据
GET /api/trades           # 交易记录
GET /api/market/<code>    # 股票行情
GET /api/status           # 系统状态
```

## 核心改进

### 1. 统一API层

```python
# V1: 分散的数据访问
with open('account.json') as f:
    data = json.load(f)

# V2: 统一API
from bobquant_v2.api import AccountAPI
api = AccountAPI()
data = api.get()  # 自动缓存、格式化
```

### 2. 标准化数据格式

```python
# 所有API返回统一格式
{
    'code': 'sh.600519',
    'name': '贵州茅台',
    'current': 1416.02,
    'change': 1.06,  # 百分比
    ...
}
```

### 3. 自动缓存

```python
# 自动3秒缓存，避免重复读取文件
data = api.get()  # 第一次读取文件
data = api.get()  # 第二次直接返回缓存
```

### 4. 批量操作

```python
# 批量获取行情（自动并行）
codes = ['sh.600519', 'sz.300750', ...]
quotes = market_api.get_batch(codes)  # 10线程并行
```

## 迁移指南

### 从V1迁移到V2

1. **数据文件**：复用V1的数据文件
   - `sim_trading/account_ideal.json`
   - `sim_trading/交易记录.json`

2. **Web界面**：使用V2的简洁模板
   - `bobquant_v2/web/templates/index.html`

3. **API调用**：使用统一接口
   ```javascript
   // V1: 多个接口
   fetch('/api/account')
   fetch('/api/positions')
   
   // V2: 一个接口
   fetch('/api/account')  // 包含所有数据
   ```

## 文件说明

| 文件 | 说明 | 行数 |
|------|------|------|
| `api/base_api.py` | API基类（缓存、工具） | ~80 |
| `api/account_api.py` | 账户数据API | ~100 |
| `api/trade_api.py` | 交易数据API | ~80 |
| `api/market_api.py` | 行情数据API | ~120 |
| `web/app.py` | Flask服务 | ~90 |
| `web/templates/index.html` | Web界面 | ~200 |
| **总计** | | **~670行** |

## 优势

1. **代码量少**：从8753行减少到670行（减少92%）
2. **维护简单**：统一接口，修改一处，全局生效
3. **性能更好**：自动缓存，批量并行
4. **易于迭代**：清晰的架构，方便添加新功能
5. **前后端分离**：API和UI独立，可以单独优化

## 后续迭代

### 添加新数据源

```python
# 只需实现get方法
class SinaDataSource(BaseAPI):
    def get(self, code):
        # 实现数据获取
        pass
```

### 添加新策略

```python
# 使用统一API获取数据
from bobquant_v2.api import AccountAPI, MarketAPI

class MyStrategy:
    def run(self):
        account = AccountAPI().get()
        quotes = MarketAPI().get_batch(codes)
        # 策略逻辑
```

### 添加新界面

```html
<!-- 只需调用统一API -->
<script>
fetch('/api/account').then(r => r.json()).then(data => {
    // 自定义展示
});
</script>
```
