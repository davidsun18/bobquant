# BobQuant UI 架构说明

## 问题分析

频繁修改UI导致数据混乱的原因是：
1. HTML、CSS、JavaScript 混在一起
2. 数据获取逻辑和UI渲染逻辑耦合
3. 修改UI时不小心破坏了数据绑定

## 解决方案

### 三层架构

```
┌─────────────────────────────────────┐
│  UI Layer (Templates)               │  ← 只负责展示，不处理数据
│  - index.html                       │
│  - 纯HTML+CSS，通过ID绑定元素       │
└─────────────────────────────────────┘
                  ↑
                  │ 调用
                  ↓
┌─────────────────────────────────────┐
│  API Layer (JavaScript)             │  ← 封装数据获取
│  - api_client.js                    │
│  - 提供标准化数据接口               │
└─────────────────────────────────────┘
                  ↑
                  │ HTTP请求
                  ↓
┌─────────────────────────────────────┐
│  Backend Layer (Flask)              │  ← 提供数据API
│  - web_ui.py                        │
│  - /api/account, /api/trades        │
└─────────────────────────────────────┘
```

## 关键原则

### 1. UI层只读
- HTML模板只负责展示
- 通过固定的ID绑定元素
- 不直接处理数据逻辑

### 2. API层封装
- 所有数据获取通过APIClient
- 统一的数据格式化
- 错误处理和缓存

### 3. 后端层独立
- Flask只提供数据接口
- 不生成HTML，只返回JSON
- 数据格式稳定

## 如何安全修改UI

### ✅ 安全操作
1. 修改CSS样式（颜色、字体、间距）
2. 调整布局（grid比例、padding）
3. 添加新的展示元素（使用新的ID）

### ❌ 危险操作
1. 修改元素ID（会破坏数据绑定）
2. 删除已有元素
3. 修改JavaScript数据逻辑

### 🔧 修改步骤

1. **备份**
   ```bash
   cp templates/index.html templates/index_backup_$(date +%Y%m%d_%H%M%S).html
   ```

2. **只修改CSS**
   - 颜色、字体、间距等纯样式

3. **测试**
   - 刷新页面检查数据是否正常显示

4. **回滚**
   - 如果出问题，立即恢复备份

## 当前稳定的UI文件

- `templates/index.html` - 当前版本
- `templates/index_stable.html` - 稳定备份

## API接口文档

### GET /api/account
返回账户数据：
```json
{
  "total_assets": 1000000,
  "market_value": 500000,
  "cash": 500000,
  "position_profit": 10000,
  "profit_today": -500,
  "positions": [...]
}
```

### GET /api/trades
返回交易记录：
```json
{
  "trades": [...]
}
```

## 建议

1. **冻结UI**：当前UI已经比较稳定，建议不再大幅修改
2. **配置化**：如需调整样式，考虑使用CSS变量
3. **版本控制**：每次修改前创建备份
4. **测试环境**：先在本地测试再部署

## 快速回滚

如果修改后出问题：
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
cp templates/index_backup_xxxxxx.html templates/index.html
pkill -f web_ui.py
python3 web_ui.py > logs/web_ui.log 2>&1 &
```
