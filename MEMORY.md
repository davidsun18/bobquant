# MEMORY.md - 量化交易团队长期记忆

## 🧠 核心记忆

### 团队成立
- **成立日期：** 2026-04-18
- **团队成员：** 7 个专业 Agent
- **核心使命：** 量化策略研发与自动化交易

---

## 📊 重要决策

### 2026-04-18 - 系统初始化
- ✅ 完成 7 个 Agent 配置
- ✅ 建立协作路由规则
- ✅ 配置定时任务
- ✅ 建立记忆与知识系统

**决策要点：**
- 采用 Boss Bot 统一协调模式
- 合规风控优先于收益
- 数据质量第一原则

### 2026-04-18 02:33 - 系统重构
- ✅ 旧量化系统 (`quant_strategies/`) 已删除
- ✅ 新多 Agent 架构已启用
- ✅ 旧策略代码备份到 `knowledge/strategies/legacy/`
- ✅ 历史回测备份到 `knowledge/backtests/legacy/`

### 2026-04-18 09:00 - 框架实现完成
- ✅ 消息队列 (基于文件系统)
- ✅ 事件总线 (WebSocket 实时推送)
- ✅ Agent 基类 (统一接口)
- ✅ 交易规则引擎 (完整 A 股规则)
- ✅ Dashboard Web UI (http://localhost:8500/dashboard)
- ✅ Data Bot (腾讯财经+BaoStock)
- ✅ Execution Bot (模拟交易)

### 2026-04-18 13:27 - 开机自启动配置完成
- ✅ openclaw-gateway.service (enabled)
- ✅ bobquant-dashboard.service (enabled)
- ✅ bobquant-execution.service (enabled)
- ✅ bobquant-data-collector.service (enabled)
- ✅ bob-quant-guard.service (enabled)
- ✅ 旧 crontab 配置已清理

**数据源配置:**
- 腾讯财经：实时行情 (默认)
- BaoStock: 历史数据
- Tushare: 基础集成

**交易配置:**
- 手续费：万三 (0.03%)
- 印花税：万分之五 (0.05%)
- T+1: 严格执行
- 初始资金：¥1,000,000

**重启后验证:**
```bash
systemctl --user status bobquant-dashboard.service
curl http://localhost:8500/api/status
```

---

## 🔬 研究发现

### 因子库初始状态
- 动量因子：5 个 (MOM_20D, MOM_60D, MOM_120D, RSV_20D, IND_MOM)
- 价值因子：4 个 (EP, BP, SP, CFOP)
- 成长因子：3 个 (REV_G, PROF_G, ASSET_G)
- 质量因子：4 个 (ROE, ROA, GPM, LEV)
- 技术因子：3 个 (VOL_20D, TURN, AMIHUD)

**总计：19 个因子**

### 策略研发状态
- 初始策略模板已创建
- 待完成首个策略回测

---

## 📈 绩效基准

### 目标设定
| 指标 | 目标值 | 说明 |
|------|--------|------|
| 年化收益 | >15% | 超越基准 7% |
| 夏普比率 | >1.0 | 风险调整后收益 |
| 最大回撤 | <-25% | 风险控制 |
| 胜率 | >55% | 交易胜率 |

---

## 📝 经验教训

### 系统建设
- Agent 协作需要清晰的通信协议
- 定时任务需要可靠的调度机制
- 记忆系统对长期决策至关重要
- 消息队列采用文件系统避免 Redis 依赖

### 待验证假设
- 动量因子在 A 股市场的有效性
- 多因子组合的稳定性
- 不同市场环境下的策略表现

---

## 🔄 更新记录

| 日期 | 更新内容 | 更新 Agent |
|------|---------|-----------|
| 2026-04-18 09:21 | 量化交易框架实现完成 - 消息队列/事件总线/Dashboard/模拟交易 | Boss Bot |
| 2026-04-18 02:33 | 系统迁移完成 - 旧量化系统 → 多 Agent 架构 | Boss Bot |
| 2026-04-18 02:00 | 初始创建 | Boss Bot |

---

## 📦 迁移记录

**2026-04-18 系统重构：**
- **旧系统：** `quant_strategies/` (单体重仓系统) → 已删除
- **新系统：** 多 Agent 协作架构 → 已启用
- **备份内容：** 旧策略代码 → `knowledge/strategies/legacy/`
- **备份内容：** 历史回测 → `knowledge/backtests/legacy/`
- **详情文档：** `memory/daily/2026-04-18_migration.md`

---

## 🔖 标签索引

#系统初始化 #因子库 #策略模板 #团队协作 #记忆系统 #系统迁移 #多 Agent 架构 #框架实现 #消息队列 #Dashboard #模拟交易 #量化引擎v2 #市场状态识别 #双级熔断 #ATR止损 #网格交易

---

## 🚀 量化交易引擎 v2.0 (2026-04-28)

### 核心改进
- **市场状态识别 (RegimeFilter)**: 基于沪深300 ADX + 波动率分位数，四级状态 (正常/预警/软熔断/硬熔断)，自动调节仓位和策略灵敏度
- **双级熔断风控**: 单股亏损≥15% → 暂停买入; 总回撤≥10% → 全局停止买入 (状态持久化)
- **ATR 动态止损**: 替代固定8%止损，止损价 = 成本价 - ATR倍数×ATR(20)，trailing stop 只升不降
- **动态网格交易**: ATR 自适应间距 + 波动率比率调整，结合市场状态门控
- **T+1 合规持仓管理**: 严格区分总持仓/可用持仓，当日买入不可卖

### 模块结构
```
quant_engine/
├── market_regime.py    # 市场状态识别
├── risk_control.py     # 双级熔断风控
├── grid_engine.py      # 动态网格交易
├── atr_stop.py         # ATR 动态止损
├── signal_generator.py # 统一信号生成器
├── position_manager.py # 持仓管理 (T+1)
├── trading_engine.py   # 主引擎
└── tests/              # 45个单元测试 (全部通过)
```

### 测试覆盖
- 45 个单元测试，覆盖率: 市场状态5 + 风控6 + 网格7 + ATR6 + 持仓8 + 信号2 + 引擎8 + 边界3 = 45
- 全部通过，0 失败
