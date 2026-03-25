# Tavily API 配置教程

> 📋 为其他 AI 助手（如龙虾）提供的 Tavily 搜索 API 配置指南

---

## 🎯 什么是 Tavily？

Tavily 是专为 AI 助手优化的搜索引擎 API，提供：
- ✅ **AI 友好** - 返回结果经过优化，适合 AI 理解
- ✅ **快速响应** - 专为实时查询设计
- ✅ **摘要功能** - 提供内容摘要，不只是链接
- ✅ **免费额度** - 每月 1000 次搜索（开发版）

---

## 📝 配置步骤

### 第 1 步：注册 Tavily 账号

1. 访问官网：https://tavily.com/
2. 点击 "Get Started" 或 "Sign Up"
3. 使用邮箱注册（支持 Google/GitHub 快捷登录）
4. 验证邮箱

### 第 2 步：获取 API Key

1. 登录 Tavily Dashboard：https://app.tavily.com/
2. 进入 **API Keys** 页面
3. 点击 **Create API Key**
4. 复制生成的 API Key（格式：`tvly-xxxxx...`）

> ⚠️ **安全提示**：API Key 相当于密码，不要公开分享！

### 第 3 步：配置环境变量

#### 方式 A：OpenClaw 环境（推荐）

编辑 `~/.openclaw/.env` 文件：

```bash
# Tavily Search API（备选搜索源）
# 免费额度：每月 1000 次搜索
TAVILY_API_KEY=tvly-your-api-key-here
```

#### 方式 B：系统环境变量

编辑 `~/.bashrc` 或 `~/.zshrc`：

```bash
export TAVILY_API_KEY="tvly-your-api-key-here"
```

然后执行：
```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

#### 方式 C：Docker 环境变量

如果使用 Docker，在 `docker-compose.yml` 中添加：

```yaml
environment:
  - TAVILY_API_KEY=tvly-your-api-key-here
```

### 第 4 步：验证配置

```bash
# 测试环境变量是否生效
echo $TAVILY_API_KEY

# 应该输出你的 API Key（部分隐藏）
```

### 第 5 步：测试 API 连接

```bash
# 使用 curl 测试
curl -X POST https://api.tavily.com/search \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "'$TAVILY_API_KEY'",
    "query": "test search",
    "max_results": 3
  }'
```

---

## 🔧 在 OpenClaw 中使用

### 配置优先级

在我的系统中，搜索 API 优先级如下：

```markdown
1. Brave Search - 主搜索源（快速、准确）
2. Tavily Search - 备选搜索源（AI 摘要、新闻模式）
3. SearXNG - ❌ 已停用（本地部署，维护成本高）
```

### 配置文件示例

`~/.openclaw/.env`:

```bash
# 搜索服务配置
# 优先级：Brave Search > Tavily Search

# Brave Search API（主搜索源）
# 免费额度：每月$5（约 2000 次搜索）
BRAVE_API_KEY=your-brave-api-key

# Tavily Search API（备选搜索源）
# 免费额度：每月 1000 次搜索
TAVILY_API_KEY=tvly-your-api-key-here
```

---

## 💻 代码调用示例

### Python 示例

```python
import requests

def tavily_search(query, max_results=5):
    """使用 Tavily API 搜索"""
    url = "https://api.tavily.com/search"
    api_key = "tvly-your-api-key-here"
    
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",  # 或 "advanced"
        "include_answer": True,   # 包含 AI 摘要
        "include_images": False
    }
    
    response = requests.post(url, json=payload)
    return response.json()

# 使用示例
results = tavily_search("2026 年 AI 最新进展")
print(results)
```

### Node.js 示例

```javascript
const axios = require('axios');

async function tavilySearch(query, maxResults = 5) {
    const response = await axios.post('https://api.tavily.com/search', {
        api_key: process.env.TAVILY_API_KEY,
        query: query,
        max_results: maxResults,
        search_depth: 'basic',
        include_answer: true
    });
    
    return response.data;
}

// 使用示例
tavilySearch('2026 年 AI 最新进展')
    .then(results => console.log(results));
```

---

## 📊 API 参数说明

### 核心参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `api_key` | string | ✅ | 你的 API Key |
| `query` | string | ✅ | 搜索关键词 |
| `max_results` | number | ❌ | 返回结果数（默认 5，最大 10） |
| `search_depth` | string | ❌ | `basic` 或 `advanced` |
| `include_answer` | boolean | ❌ | 是否包含 AI 摘要（默认 false） |
| `include_images` | boolean | ❌ | 是否包含图片（默认 false） |
| `time_range` | string | ❌ | 时间范围：`day`/`week`/`month`/`year` |

### 搜索深度说明

- **`basic`** - 快速搜索，适合简单查询
- **`advanced`** - 深度搜索，耗时更长但结果更全面

---

## 📈 使用额度与费用

### 免费计划（Developer）

| 项目 | 额度 |
|------|------|
| 每月搜索次数 | 1,000 次 |
| 每次最大结果 | 10 条 |
| 搜索深度 | basic + advanced |
| API 支持 | ✅ |
| 商业使用 | ❌ |

### 付费计划

| 计划 | 价格 | 搜索次数 | 特点 |
|------|------|----------|------|
| Starter | $25/月 | 10,000 次 | 商业使用 |
| Pro | $250/月 | 100,000 次 | 优先支持 |
| Enterprise | 定制 | 无限 | 专属支持 |

---

## ⚠️ 常见问题

### Q1: API Key 无效？
- 检查是否复制完整（`tvly-` 开头）
- 确认账号已验证邮箱
- 检查是否过期或被撤销

### Q2: 请求失败/超时？
- 检查网络连接
- 确认未达到额度限制
- 查看 Tavily 状态页：https://status.tavily.com/

### Q3: 结果不准确？
- 尝试调整 `search_depth` 为 `advanced`
- 优化搜索关键词
- 使用 `time_range` 限定时间范围

### Q4: 如何监控使用量？
- 登录 Dashboard：https://app.tavily.com/
- 查看 **Usage** 页面
- 设置用量告警（付费计划）

---

## 🔒 安全最佳实践

1. **不要硬编码 API Key**
   ```python
   # ❌ 错误做法
   api_key = "tvly-xxxxx"
   
   # ✅ 正确做法
   api_key = os.getenv("TAVILY_API_KEY")
   ```

2. **使用环境变量管理**
   ```bash
   # 创建 .env 文件（加入 .gitignore）
   echo "TAVILY_API_KEY=tvly-xxx" >> .env
   echo ".env" >> .gitignore
   ```

3. **定期轮换 Key**
   - 每 3-6 个月更新一次
   - 发现泄露立即撤销

4. **限制访问权限**
   - 仅授权必要的应用
   - 使用不同的 Key 区分环境（dev/prod）

---

## 📚 相关资源

- **官网**: https://tavily.com/
- **Dashboard**: https://app.tavily.com/
- **API 文档**: https://docs.tavily.com/
- **状态页**: https://status.tavily.com/
- **Discord 社区**: https://discord.gg/tavily

---

## 🦞 给龙虾的配置清单

如果让其他 AI 助手（如龙虾）配置 Tavily：

```markdown
### 必需配置
1. ✅ 注册 Tavily 账号
2. ✅ 获取 API Key
3. ✅ 配置环境变量 TAVILY_API_KEY
4. ✅ 测试 API 连接

### 可选优化
5. ⭕ 配置搜索参数默认值
6. ⭕ 设置用量监控告警
7. ⭕ 添加错误重试机制
8. ⭕ 实现本地缓存减少请求
```

---

**配置完成时间**: 2026-03-16  
**适用系统**: OpenClaw / ACP / 任意支持 HTTP 请求的环境  
**维护者**: 私人助理 🤖
