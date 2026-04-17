# BobQuant 故障排查指南

常见问题和解决方案。

---

## 📋 目录

1. [安装问题](#安装问题)
2. [配置问题](#配置问题)
3. [数据问题](#数据问题)
4. [策略问题](#策略问题)
5. [交易问题](#交易问题)
6. [看板问题](#看板问题)
7. [性能问题](#性能问题)
8. [系统问题](#系统问题)

---

## 安装问题

### 1. pip 安装失败

**错误**:
```
ERROR: Could not find a version that satisfies the requirement xxx
```

**解决方案**:

```bash
# 1. 升级 pip
pip install --upgrade pip

# 2. 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 检查 Python 版本
python3 --version  # 需要 3.10+

# 4. 使用虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. TA-Lib 安装失败

**错误**:
```
build/temp.linux-x86_64/talib.c:4:10: fatal error: ta-lib/ta_defs.h: No such file or directory
```

**解决方案**:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install libta-lib-dev
pip install ta-lib

# macOS
brew install ta-lib
pip install ta-lib

# Windows
# 1. 下载预编译包
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
# 2. 安装
pip install TA_Lib‑0.4.24‑cp311‑cp311‑win_amd64.whl

# 或者使用 conda
conda install -c conda-forge ta-lib
```

### 3. 依赖冲突

**错误**:
```
ERROR: Cannot install xxx and yyy because these package versions have conflicting dependencies.
```

**解决方案**:

```bash
# 1. 清理缓存
pip cache purge

# 2. 卸载冲突包
pip uninstall pandas numpy

# 3. 重新安装
pip install -r requirements.txt

# 4. 或使用 pip-tools
pip install pip-tools
pip-compile requirements.in
pip-sync requirements.txt
```

---

## 配置问题

### 1. 配置文件加载失败

**错误**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'config/settings.json5'
```

**解决方案**:

```bash
# 1. 检查文件是否存在
ls -la config/settings.json5

# 2. 复制示例配置
cp config/config_example.json5 config/settings.json5

# 3. 检查路径
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
python3 -c "from bobquant.config import ConfigLoader; print(ConfigLoader('config/settings.json5').load())"
```

### 2. JSON5 语法错误

**错误**:
```
json5.lib.syntax.Error: Expecting value: line 10 column 5
```

**解决方案**:

```bash
# 1. 使用 JSON5 验证器
python3 -c "import json5; print(json5.load(open('config/settings.json5')))"

# 2. 检查常见错误
# - 缺少逗号
# - 多余的逗号 (最后一个元素后)
# - 引号不匹配
# - 注释格式错误

# 正确的 JSON5 格式
{
  "key": "value",  // 行注释
  "array": [1, 2, 3,],  // 尾随逗号允许
  /* 块注释 */
}
```

### 3. SecretRef 解析失败

**错误**:
```
ValueError: Cannot resolve SecretRef: env variable BOBQUANT_API_KEY not found
```

**解决方案**:

```bash
# 1. 检查环境变量
echo $BOBQUANT_API_KEY

# 2. 设置环境变量
export BOBQUANT_API_KEY="your_key"

# 3. 或写入 .env 文件
echo "BOBQUANT_API_KEY=your_key" > .env

# 4. 加载 .env 文件
python3 -c "from dotenv import load_dotenv; load_dotenv()"

# 5. 检查文件权限 (文件方式)
cat ~/.bobquant/secret.txt
chmod 600 ~/.bobquant/secret.txt
```

### 4. 配置验证失败

**错误**:
```
ValidationError: 5 validation errors for BobQuantConfig
```

**解决方案**:

```python
from bobquant.config import ConfigLoader, ConfigValidator

loader = ConfigLoader("config/settings.json5")
config = loader.load()

validator = ConfigValidator(config)
if not validator.validate_all():
    print(validator.get_error_report())
    
    # 查看具体错误
    for error in validator.get_errors():
        print(f"字段：{error.field}")
        print(f"错误：{error.message}")
        print(f"建议：{error.suggestion}")
```

---

## 数据问题

### 1. 数据获取失败

**错误**:
```
DataError: Failed to fetch data for 600519.SH
```

**解决方案**:

```bash
# 1. 检查数据源连接
python3 -c "
from bobquant.data import get_market_data
df = get_market_data('600519.SH', '1d', '2023-01-01', '2023-01-31')
print(df.head())
"

# 2. 检查 Tushare Token
echo $TUSHARE_TOKEN
python3 -c "import tushare as ts; ts.set_token('your_token'); print(ts.pro_api())"

# 3. 检查网络
ping api.tushare.pro
curl -I https://api.tushare.pro

# 4. 切换数据源
# config/settings.json5:
# {"data": {"provider": "akshare"}}
```

### 2. 数据格式错误

**错误**:
```
KeyError: 'close'
```

**解决方案**:

```python
# 1. 检查数据列
df = get_market_data("600519.SH")
print(df.columns)

# 2. 重命名列
df = df.rename(columns={
    '收盘价': 'close',
    '开盘价': 'open',
    '最高价': 'high',
    '最低价': 'low',
    '成交量': 'volume'
})

# 3. 检查数据类型
print(df.dtypes)

# 4. 处理缺失值
df = df.dropna()  # 或删除缺失值
df = df.fillna(method='ffill')  # 或前向填充
```

### 3. 数据缓存问题

**错误**:
```
FileNotFoundError: data/cache/600519.SH_1d.pkl
```

**解决方案**:

```bash
# 1. 清除缓存
rm -rf data/cache/*

# 2. 禁用缓存
# config/settings.json5:
# {"data": {"cache_enabled": false}}

# 3. 检查缓存目录权限
ls -la data/cache/
chmod 755 data/cache/
```

### 4. 实时数据延迟

**问题**: 实时数据更新慢

**解决方案**:

```python
# 1. 检查数据刷新频率
# Streamlit: @st.cache_data(ttl=30)  # 30 秒刷新
# Dash: interval=3000  # 3 秒刷新

# 2. 优化查询
# 只查询需要的股票
symbols = ["600519.SH"]  # 而不是全市场
tick = get_realtime_data(symbols)

# 3. 使用更快的数据源
# 腾讯财经 > Tushare > AkShare (速度)
```

---

## 策略问题

### 1. 策略不产生信号

**问题**: 策略运行但没有交易信号

**排查步骤**:

```python
# 1. 添加调试日志
def on_bar(self, bar):
    self.logger.debug(f"on_bar: {bar.symbol} {bar.close}")
    self.logger.debug(f"MA5={self.ma5.value}, MA20={self.ma20.value}")
    self.logger.debug(f"持仓={self.get_position(bar.symbol)}")
    
    if self.should_buy(bar):
        self.logger.info("买入信号!")
        self.buy(bar.symbol, 100)

# 2. 检查指标计算
print(f"数据长度：{len(self.data)}")
print(f"MA5 有效：{self.ma5.value is not None}")

# 3. 检查条件
# 单独测试条件
condition1 = self.ma5.value > self.ma20.value
condition2 = self.get_position(bar.symbol) == 0
print(f"条件 1: {condition1}, 条件 2: {condition2}")

# 4. 检查数据
print(self.data.tail())
```

### 2. 策略报错

**错误**:
```
AttributeError: 'MyStrategy' object has no attribute 'ma5'
```

**解决方案**:

```python
# 1. 检查 on_init 是否被调用
def on_init(self):
    self.logger.info("on_init 被调用")
    self.ma5 = MA(5)

# 2. 确保在 on_bar 之前初始化
def on_bar(self, bar):
    if not hasattr(self, 'ma5'):
        self.logger.error("ma5 未初始化!")
        return
    self.ma5.update(bar.close)

# 3. 检查继承
class MyStrategy(Strategy):  # 确保继承 Strategy
    def __init__(self):
        super().__init__()  # 调用父类初始化
```

### 3. 回测结果异常

**问题**: 回测收益率过高或过低

**排查步骤**:

```python
# 1. 检查手续费设置
engine = BacktestEngine(
    commission_rate=0.0005,  # 万分之五
    slippage=0.001           # 千分之一滑点
)

# 2. 检查未来函数
# 错误：使用了收盘价决定开盘买入
if bar.close > bar.open:  # 收盘时才知道
    self.buy(bar.symbol, 100)  # 但要在开盘买入

# 正确：使用开盘价
if bar.close > bar.open:
    self.buy(bar.symbol, 100, price=bar.open)

# 3. 检查幸存者偏差
# 使用包含退市股票的数据集
universe = get_stock_universe(include_delisted=True)

# 4. 检查复权
# 使用后复权数据避免价格跳空
df = get_data(symbol, adjusted="post")
```

### 4. 策略性能差

**问题**: 实盘表现远差于回测

**解决方案**:

```python
# 1. 增加滑点
engine = BacktestEngine(slippage=0.002)  # 增加到 0.2%

# 2. 考虑冲击成本
# 大单会影响价格
impact_cost = quantity / avg_volume * 0.01

# 3. 检查流动性
# 避免交易流动性差的股票
if avg_volume < 1000000:
    continue  # 跳过

# 4. 考虑停牌
# 回测时排除停牌股票
df = df[df['volume'] > 0]
```

---

## 交易问题

### 1. 下单失败

**错误**:
```
ExecutionError: Order rejected: insufficient funds
```

**解决方案**:

```python
# 1. 检查可用资金
print(f"总资产：{self.account.total_assets}")
print(f"可用资金：{self.account.available_cash}")
print(f"冻结资金：{self.account.frozen_cash}")

# 2. 检查仓位限制
print(f"单票仓位：{position_pct}")
print(f"总仓位：{total_position_pct}")

# 3. 检查订单参数
print(f"订单数量：{quantity}")
print(f"订单金额：{quantity * price}")

# 4. 检查风控
result = risk_check(symbol, quantity, price)
if not result.passed:
    print(f"风控失败：{result.message}")
```

### 2. 订单状态异常

**问题**: 订单一直未成交

**解决方案**:

```python
# 1. 检查订单状态
order = get_order(order_id)
print(f"状态：{order.status}")
print(f"已成交：{order.filled_quantity}/{order.quantity}")

# 2. 检查价格
print(f"委托价：{order.price}")
print(f"市场价：{get_current_price(symbol)}")

# 3. 撤单重下
if order.status == "pending" and timeout > 60:
    cancel_order(order_id)
    # 调整价格重新下单
    new_price = get_current_price(symbol) * 1.01  # 提高 1%
    place_order(symbol, quantity, new_price)
```

### 3. 重复下单

**问题**: 同一信号产生多个订单

**解决方案**:

```python
# 1. 添加信号标志
self.last_signal = None

def on_bar(self, bar):
    signal = self.calculate_signal()
    
    # 信号变化时才交易
    if signal != self.last_signal:
        if signal == "buy":
            self.buy(bar.symbol, 100)
        elif signal == "sell":
            self.sell(bar.symbol, 100)
        self.last_signal = signal

# 2. 检查持仓
if self.get_position(bar.symbol) > 0:
    return  # 已有持仓，不再买入

# 3. 检查 pending 订单
pending = get_pending_orders(symbol)
if pending:
    return  # 已有 pending 订单
```

### 4. 止损未触发

**问题**: 价格跌破止损价但未卖出

**解决方案**:

```python
# 1. 检查止损设置
sl = get_stop_loss(symbol)
print(f"止损价：{sl.stop_loss_price}")
print(f"当前价：{current_price}")

# 2. 手动检查止损
def check_stop_loss():
    for symbol, position in self.positions.items():
        sl = self.get_stop_loss(symbol)
        if sl and current_price <= sl.stop_loss_price:
            self.logger.info(f"止损触发：{symbol}")
            self.sell(symbol, position.volume)

# 3. 在 on_bar 中调用
def on_bar(self, bar):
    self.check_stop_loss()  # 每根 K 线检查
```

---

## 看板问题

### 1. Streamlit 无法启动

**错误**:
```
Port 8501 is already in use
```

**解决方案**:

```bash
# 1. 检查占用端口的进程
lsof -i :8501
netstat -tlnp | grep 8501

# 2. 杀死进程
kill $(lsof -t -i:8501)
pkill -f "streamlit run"

# 3. 使用其他端口
streamlit run web/streamlit_app.py --server.port 8503

# 4. 查看日志
tail -f /tmp/streamlit.log
```

### 2. 看板数据显示异常

**问题**: 看板显示的数据不正确或为空

**解决方案**:

```python
# 1. 检查数据文件
ls -la logs/account.json
ls -la logs/positions.json
ls -la logs/trades.json

# 2. 检查数据内容
cat logs/account.json
python3 -c "import json; print(json.load(open('logs/account.json')))"

# 3. 刷新缓存
# Streamlit 页面点击"刷新"按钮
# 或清除缓存文件
rm -rf ~/.streamlit/cache/*

# 4. 检查数据更新
# 确保主程序在运行并更新数据文件
ps aux | grep "python3 main.py"
```

### 3. 看板加载慢

**问题**: 页面加载时间过长

**解决方案**:

```python
# 1. 优化数据加载
@st.cache_data(ttl=30)
def load_data():
    return pd.read_json("logs/account.json")

# 2. 减少数据量
# 只加载最近 N 天的数据
df = df[df['date'] > (today - timedelta(days=30))]

# 3. 优化图表
# 减少数据点
df = df.resample('W').last()  # 日线转周线

# 4. 使用子缓存
@st.cache_data
def load_positions():
    ...

@st.cache_data
def load_trades():
    ...
```

### 4. 看板无法访问

**问题**: 浏览器无法访问看板

**解决方案**:

```bash
# 1. 检查服务是否运行
ps aux | grep streamlit
netstat -tlnp | grep 8501

# 2. 检查防火墙
sudo ufw status
sudo ufw allow 8501

# 3. 检查绑定地址
# 应该绑定 0.0.0.0 而不是 127.0.0.1
streamlit run app.py --server.address 0.0.0.0

# 4. 测试连接
curl http://localhost:8501
curl http://192.168.50.55:8501

# 5. 检查服务器日志
tail -f /tmp/streamlit.log
```

---

## 性能问题

### 1. 内存占用高

**问题**: 进程内存占用过高

**解决方案**:

```python
# 1. 检查内存使用
import tracemalloc
tracemalloc.start()

# ... 运行代码 ...

current, peak = tracemalloc.get_traced_memory()
print(f"当前内存：{current / 1024 / 1024:.2f} MB")
print(f"峰值内存：{peak / 1024 / 1024:.2f} MB")
tracemalloc.stop()

# 2. 释放不用的数据
del large_dataframe
import gc
gc.collect()

# 3. 使用 generator
def process_data():
    for chunk in read_chunks():
        yield process(chunk)

# 4. 限制缓存大小
from functools import lru_cache

@lru_cache(maxsize=100)  # 限制缓存数量
def cached_function(x):
    ...
```

### 2. CPU 占用高

**问题**: CPU 使用率持续 100%

**解决方案**:

```python
# 1. 检查循环
# 避免无限循环
while True:  # 错误
    process()

while running:  # 正确
    process()
    time.sleep(1)  # 添加休眠

# 2. 优化计算
# 使用向量化代替循环
# 错误
result = []
for x in data:
    result.append(x * 2)

# 正确
result = data * 2

# 3. 使用多进程
from multiprocessing import Pool

with Pool(4) as p:
    results = p.map(process, data_list)
```

### 3. 磁盘空间不足

**问题**: 磁盘空间被日志填满

**解决方案**:

```bash
# 1. 检查磁盘使用
df -h
du -sh logs/*

# 2. 配置日志轮转
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'bobquant.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)

# 3. 清理旧日志
find logs/ -name "*.log" -mtime +7 -delete

# 4. 清理缓存
rm -rf data/cache/*
rm -rf ~/.streamlit/cache/*
```

---

## 系统问题

### 1. 进程崩溃

**问题**: 主程序意外退出

**解决方案**:

```bash
# 1. 查看日志
tail -n 100 logs/bobquant.log

# 2. 检查错误
grep -i "error" logs/bobquant.log
grep -i "exception" logs/bobquant.log

# 3. 使用守护进程
nohup python3 main.py > /tmp/bobquant.log 2>&1 &

# 4. 使用 systemd
sudo systemctl status bobquant
sudo journalctl -u bobquant -n 100

# 5. 自动重启
# crontab -e
*/5 * * * * ps aux | grep "python3 main.py" | grep -v grep || cd /path && python3 main.py &
```

### 2. 网络连接问题

**问题**: 无法连接 API 或数据源

**解决方案**:

```bash
# 1. 检查网络
ping api.tushare.pro
curl -I https://api.tushare.pro

# 2. 检查 DNS
cat /etc/resolv.conf
nslookup api.tushare.pro

# 3. 使用备用 DNS
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf

# 4. 检查代理
echo $http_proxy
echo $https_proxy

# 5. 测试 API
python3 -c "
import requests
r = requests.get('https://api.tushare.pro', timeout=5)
print(r.status_code)
"
```

### 3. 权限问题

**错误**:
```
PermissionError: [Errno 13] Permission denied
```

**解决方案**:

```bash
# 1. 检查文件权限
ls -la config/settings.json5
ls -la logs/

# 2. 修复权限
chmod 644 config/settings.json5
chmod 755 logs/
chown openclaw:openclaw logs/*

# 3. 检查目录权限
ls -la /home/openclaw/.openclaw/workspace/

# 4. 以正确用户运行
sudo -u openclaw python3 main.py
```

### 4. 时间同步问题

**问题**: 系统时间不准确导致交易问题

**解决方案**:

```bash
# 1. 检查时间
date
timedatectl

# 2. 同步时间
sudo timedatectl set-ntp true
sudo ntpdate ntp.aliyun.com

# 3. 设置时区
sudo timedatectl set-timezone Asia/Shanghai

# 4. 验证
timedatectl
```

---

## 诊断工具

### 1. 系统健康检查

```python
#!/usr/bin/env python3
"""系统健康检查脚本"""

import os
import sys
import json
from datetime import datetime

def check_system():
    results = {}
    
    # 检查 Python 版本
    results['python_version'] = sys.version
    
    # 检查配置文件
    results['config_exists'] = os.path.exists('config/settings.json5')
    
    # 检查数据目录
    results['data_dir_exists'] = os.path.exists('data/')
    
    # 检查日志目录
    results['logs_dir_exists'] = os.path.exists('logs/')
    
    # 检查进程
    import subprocess
    result = subprocess.run(
        ['ps', 'aux'],
        capture_output=True,
        text=True
    )
    results['main_process_running'] = 'python3 main.py' in result.stdout
    
    # 检查端口
    result = subprocess.run(
        ['netstat', '-tlnp'],
        capture_output=True,
        text=True
    )
    results['port_8501_listening'] = ':8501' in result.stdout
    
    # 打印结果
    print("=" * 50)
    print("系统健康检查")
    print("=" * 50)
    for key, value in results.items():
        status = "✅" if value else "❌"
        print(f"{status} {key}: {value}")
    
    return all(results.values())

if __name__ == "__main__":
    healthy = check_system()
    sys.exit(0 if healthy else 1)
```

### 2. 配置验证脚本

```python
#!/usr/bin/env python3
"""配置验证脚本"""

from bobquant.config import ConfigLoader, ConfigValidator
import sys

def validate_config():
    try:
        loader = ConfigLoader("config/settings.json5")
        config = loader.load()
        
        validator = ConfigValidator(config)
        
        print("=" * 50)
        print("配置验证")
        print("=" * 50)
        
        # Schema 验证
        if validator.validate_schema():
            print("✅ Schema 验证通过")
        else:
            print("❌ Schema 验证失败")
            for error in validator.get_errors():
                print(f"  - {error}")
        
        # 业务规则验证
        if validator.validate_business_rules():
            print("✅ 业务规则验证通过")
        else:
            print("❌ 业务规则验证失败")
            print(validator.get_error_report())
        
        # SecretRef 验证
        if validator.validate_secrets():
            print("✅ SecretRef 验证通过")
        else:
            print("❌ SecretRef 验证失败")
            for error in validator.get_errors():
                print(f"  - {error}")
        
        # 总体结果
        if validator.validate_all():
            print("\n✅ 配置验证通过!")
            return True
        else:
            print("\n❌ 配置验证失败!")
            return False
            
    except Exception as e:
        print(f"❌ 验证过程出错：{e}")
        return False

if __name__ == "__main__":
    valid = validate_config()
    sys.exit(0 if valid else 1)
```

---

## 获取帮助

### 1. 查看日志

```bash
# 主程序日志
tail -f logs/bobquant.log

# Streamlit 日志
tail -f /tmp/streamlit.log

# 系统日志
journalctl -u bobquant -f
```

### 2. 收集诊断信息

```bash
# 运行诊断脚本
python3 scripts/diagnose.py

# 收集日志
tar -czf diagnosis_$(date +%Y%m%d).tar.gz \
    logs/*.log \
    config/settings.json5 \
    /tmp/streamlit.log
```

### 3. 提交 Issue

在 GitHub 提交 Issue 时，请包含：

1. 问题描述
2. 错误信息 (完整 traceback)
3. 环境信息 (Python 版本、操作系统)
4. 复现步骤
5. 诊断信息

---

## 快速参考

### 常用命令

```bash
# 重启服务
pkill -f "python3 main.py"
pkill -f "streamlit run"
./start_all.sh

# 查看状态
ps aux | grep python3
netstat -tlnp | grep -E "8501|8050"

# 清理缓存
rm -rf data/cache/*
rm -rf ~/.streamlit/cache/*

# 更新代码
git pull
pip install -r requirements.txt

# 备份
./scripts/backup.sh
```

### 紧急处理

```bash
# 停止所有交易
pkill -f "python3 main.py"

# 平仓 (如果需要)
python3 scripts/close_all.py

# 发送告警
python3 scripts/send_alert.py "紧急停止"
```

---

**最后更新**: 2026-04-11  
**维护者**: BobQuant Team
