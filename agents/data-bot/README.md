# Data Bot - 数据采集模块

## 📋 概述

Data Bot 负责量化交易系统的**数据采集、清洗、校验和存储**工作。

### 数据源

| 数据源 | 类型 | 用途 | 状态 |
|--------|------|------|------|
| 腾讯财经 | 实时行情 | 实时股价、涨跌幅、成交量 | ✅ 启用 |
| BaoStock | 历史数据 | 历史 K 线、复权数据 | ✅ 启用 |
| iTick | Level2 行情 | 高频交易数据 | ❌ 禁用 (DNS 问题) |

---

## 🚀 快速开始

### 1. 测试 API 连接

```bash
cd /home/openclaw/.openclaw/workspace/agents/data-bot/scripts
python3 test_api.py
```

### 2. 采集实时行情

```bash
python3 collect_data.py
```

### 3. 采集历史数据

编辑 `collect_data.py`，取消注释：
```python
collect_history_data()
```

然后运行：
```bash
python3 collect_data.py
```

---

## 📁 目录结构

```
data-bot/
├── config.json          # 配置文件
├── README.md            # 本文档
├── scripts/
│   ├── collect_data.py  # 主采集脚本
│   └── test_api.py      # API 测试脚本
└── ...
```

### 数据存储路径

```
workspace/
├── data/
│   ├── raw/             # 原始数据 (Parquet 格式)
│   ├── processed/       # 处理后的数据 (按日期分区)
│   └── backup/          # 数据备份
└── logs/
    └── data_bot_YYYY-MM-DD.log
```

---

## ⚙️ 配置说明

### config.json

```json
{
  "data_sources": {
    "primary": {
      "name": "腾讯财经",
      "timeout_ms": 1000,
      "retry_count": 3
    },
    "historical": {
      "name": "BaoStock"
    }
  },
  "collection_schedule": {
    "tasks": [
      {"name": "盘前数据采集", "cron": "30 8 * * 1-5"},
      {"name": "午间数据备份", "cron": "30 11 * * 1-5"},
      {"name": "盘后数据归档", "cron": "0 16 * * 1-5"}
    ]
  }
}
```

---

## 📊 数据格式

### 实时行情数据 (quote)

| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | string | 股票代码 |
| stock_name | string | 股票名称 |
| current_price | float | 当前价格 |
| prev_close | float | 昨收价 |
| open_price | float | 开盘价 |
| high_price | float | 最高价 |
| low_price | float | 最低价 |
| change | float | 涨跌额 |
| change_pct | float | 涨跌幅 (%) |
| buy1_price | float | 买一价 |
| buy1_volume | int | 买一量 |
| sell1_price | float | 卖一价 |
| sell1_volume | int | 卖一量 |
| volume | int | 成交量 (手) |
| turnover | float | 成交额 (元) |
| timestamp | string | 时间戳 |
| source | string | 数据源 |

### 历史数据 (history)

| 字段 | 类型 | 说明 |
|------|------|------|
| date | string | 日期 |
| open | float | 开盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| close | float | 收盘价 |
| volume | int | 成交量 |
| amount | float | 成交额 |
| adjustflag | string | 复权状态 |
| stock_code | string | 股票代码 |
| source | string | 数据源 |

---

## 🔧 高级用法

### 自定义股票列表

编辑 `collect_data.py` 中的 `load_stock_list()` 函数：

```python
def load_stock_list() -> List[str]:
    return [
        '600519',  # 贵州茅台
        '000001',  # 平安银行
        # 添加更多股票...
    ]
```

### 修改采集频率

编辑 `config.json` 中的 `collection_schedule` 字段。

### 数据验证规则

编辑 `DataValidator` 类中的验证逻辑。

---

## ⚠️ 注意事项

1. **交易时段**: 数据采集应在交易时段内进行 (09:30-11:30, 13:00-15:00)
2. **请求频率**: 避免过快请求，已内置延迟控制
3. **周末/节假日**: 非交易日无实时数据，历史数据不受影响
4. **数据备份**: 重要数据已自动备份到 `backup/` 目录

---

## 📝 日志查看

```bash
# 查看今日日志
tail -f /home/openclaw/.openclaw/workspace/logs/data_bot_$(date +%Y-%m-%d).log

# 查看错误日志
grep ERROR /home/openclaw/.openclaw/workspace/logs/data_bot_*.log
```

---

## 🛠️ 故障排查

### 腾讯财经超时

- 检查网络连接
- 增加 `TENCENT_TIMEOUT` 配置值
- 检查防火墙设置

### BaoStock 登录失败

- 检查 BaoStock 库是否安装：`pip3 show baostock`
- 检查网络连接
- 查看 BaoStock 官方文档确认服务状态

### 数据保存失败

- 检查磁盘空间：`df -h`
- 检查目录权限：`ls -la /home/openclaw/.openclaw/workspace/data/`

---

## 📞 支持

- 文档：`/home/openclaw/.openclaw/workspace/docs/`
- 日志：`/home/openclaw/.openclaw/workspace/logs/`
- 配置：`/home/openclaw/.openclaw/workspace/agents/data-bot/config.json`

---

**版本**: 1.0.0  
**更新日期**: 2026-04-18  
**维护者**: Data Bot
