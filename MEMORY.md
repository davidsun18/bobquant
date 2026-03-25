# MEMORY.md - 长期记忆

## 👥 人物

**David**
- 位置：中国，时区 Asia/Shanghai
- 兴趣：编程（新手，刚开始学习）
- 状态：需要引导和学习支持

---

## ⚙️ 系统配置

### Agent 配置
- **工具权限**: `full`（所有工具已启用）
- **配置文件**: `/home/openclaw/.openclaw/openclaw.json`

### API Keys
- **Brave Search**: 已配置 (`tools.web.search.apiKey`) - 主搜索源
- **Tavily Search**: 已配置 (`~/.openclaw/.env`) - 备选搜索源，每月 1000 次免费额度
- **阿里云百炼**: 已配置 (qwen3.5-plus 模型)

### 技能
- **cf-fetcher**: 网页抓取技能
  - 位置：`/home/openclaw/.openclaw/workspace/skills/cf-fetcher/`
  - 功能：高效抓取网页，优先 Markdown 格式，节省 Token
  - 依赖：`requests`, `html-to-markdown` ✅ 已安装
  - **优先级**: 抓取网页内容时优先使用此技能

### 自定义脚本
- **tavily_search.py**: Tavily API 搜索脚本
  - 位置：`/home/openclaw/.openclaw/workspace/scripts/tavily_search.py`
  - 用法：`python3 scripts/tavily_search.py "搜索关键词" [结果数] [深度]`
  - API Key: 从 `~/.openclaw/.env` 读取
  - **使用场景**: 需要 AI 摘要、新闻搜索、深度搜索时

---

## 📅 重要日期

- **2026-03-16**: Bob 首次上线，与 David 相识

---

## 🎯 当前项目

1. **量化交易模拟盘** - A 股量化策略系统
   - 引擎：三阶段（做T/风控/策略信号），金字塔加仓，分批止盈
   - 数据源：腾讯财经（主力），Infoway WebSocket（测试中，API Key 有效但连接不稳）
   - 守护：process_guard.py 自动管理 web_ui + streamlit + 交易引擎
   - 股票池：50 只（银行/白酒/科技/新能源/医药/消费/周期）
   - 位置：`/home/openclaw/.openclaw/workspace/quant_strategies/`

2. **Python 入门教学** - David 想学编程，从 Python 开始
   - 状态：等待 David 安装 Python 环境
   - 系统：Windows

---

## 💡 偏好与习惯

- **A 股颜色**：红涨绿跌！不要用美股习惯（绿涨红跌）
- **网页抓取**: 优先使用 cf-fetcher 技能（节省 Token）
- **搜索优先级**: 
  1. **Brave Search** (`web_search` 工具) - ⭐ 优先使用，快速准确
  2. **Tavily Search** (`scripts/tavily_search.py`) - 备选，AI 摘要、新闻模式、深度搜索

---

_最后更新：2026-03-16_
