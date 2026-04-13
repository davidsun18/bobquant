# Claude Code 泄露源码学习报告

**学习时间**: 2026-04-11  
**源码来源**: https://github.com/codeaashu/claude-code  
**泄露方式**: npm package 中的 .map 文件泄露  
**代码规模**: ~512,000 行，1,900+ 文件  

---

## 📊 核心架构

### 技术栈
| 组件 | 技术 |
|------|------|
| **运行时** | Bun (非 Node.js) |
| **语言** | TypeScript (strict) |
| **终端 UI** | React + Ink |
| **CLI 框架** | Commander.js |
| **状态管理** | React Context + Store |
| **样式** | Chalk (终端颜色) |

### 核心管道
```
用户输入 → CLI 解析 → Query Engine → LLM API → 工具执行循环 → 终端 UI
```

---

## 🏗️ 核心模块

### 1. QueryEngine.ts (46K 行)
**功能**: 整个系统的心脏
- 流式响应处理
- 工具调用循环
- Thinking 模式支持
- 自动重试机制
- Token 计数和成本追踪
- 上下文窗口管理

### 2. 工具系统 (src/tools/)
**~40 个工具**，每个工具自包含：
- 输入 schema (Zod 验证)
- 权限模型
- 执行逻辑
- UI 组件

**核心工具分类**:
| 分类 | 工具 |
|------|------|
| **文件系统** | FileRead/FileWrite/FileEdit/Glob/Grep |
| **Shell 执行** | Bash/PowerShell/REPL |
| **Agent 编排** | Agent/TeamCreate/Sleep |
| **任务管理** | TaskCreate/TaskUpdate/TaskList |
| **Web** | WebFetch/WebSearch |
| **MCP** | MCPTool/ListMcpResources |
| **集成** | LSPTool/SkillTool |

### 3. 命令系统 (src/commands/)
**~85 个斜杠命令**:
- **PromptCommand**: `/review`, `/commit` - 发送格式化 prompt
- **LocalCommand**: `/cost`, `/version` - 本地执行
- **LocalJSXCommand**: `/doctor`, `/install` - 返回 React JSX

### 4. 状态管理
- `AppStateStore.ts` - 全局可变状态
- Context Providers - React context
- Selectors - 派生状态函数
- Change Observers - 状态变更副作用

---

## 🎨 UI 架构

### 组件系统 (src/components/)
- **140+ 组件**: 功能性 React 组件
- **Ink 原语**: Box, Text, useInput()
- **设计系统**: src/components/design-system/

### Hooks (src/hooks/)
- **80+ hooks**: 标准 React hooks 模式
- **权限 hooks**: useCanUseTool, useToolPermission
- **IDE 集成**: useIDEIntegration
- **输入处理**: useTextInput, useVimInput
- **会话管理**: useSessionBackgrounding

### 屏幕 (src/screens/)
- REPL.tsx - 主交互界面
- Doctor.tsx - 环境诊断
- ResumeConversation.tsx - 会话恢复

---

## 🔐 权限系统

### 权限模式
| 模式 | 行为 |
|------|------|
| default | 每次破坏性操作都询问用户 |
| plan | 显示完整计划，询问一次 |
| bypassPermissions | 自动批准所有 (危险) |
| auto | ML 分类器决定 |

### 权限规则 (通配符模式)
```
Bash(git *)           # 允许所有 git 命令
FileEdit(/src/*)      # 允许编辑 src/ 下任何文件
FileRead(*)           # 允许读取任何文件
```

---

## ⚡ 构建系统

### Bun 运行时特性
- 原生 JSX/TSX 支持 (无需转译)
- `bun:bundle` feature flags
- ES modules + `.js` 扩展名

### Feature Flags (死代码消除)
```typescript
import { feature } from 'bun:bundle'

if (feature('VOICE_MODE')) {
  const voiceCommand = require('./commands/voice/index.js').default
}
```

**关键 flags**:
- PROACTIVE - 主动代理模式
- KAIROS - Kairos 子系统
- BRIDGE_MODE - IDE 桥接
- DAEMON - 后台守护进程
- VOICE_MODE - 语音输入/输出

---

## 💡 可借鉴的设计

### 1. 工具系统设计
**优点**:
- 自包含模块，职责清晰
- 统一的输入/输出 schema
- 权限检查内置
- UI 渲染解耦

**可借鉴到 BobQuant**:
```python
# BobQuant 工具系统
class BaseTool(ABC):
    name: str
    input_schema: dict
    permission_required: bool
    
    @abstractmethod
    def execute(self, args, context) -> ToolResult:
        pass
    
    def check_permission(self, args, context) -> bool:
        pass
```

### 2. Query Engine 模式
**优点**:
- 流式处理，低延迟
- 自动重试，容错性强
- Token 追踪，成本透明

**可借鉴到 BobQuant**:
```python
class QueryEngine:
    async def stream_query(self, query):
        async for chunk in self.llm.stream(query):
            yield chunk
            if chunk.tool_call:
                result = await self.execute_tool(chunk.tool_call)
                yield result
```

### 3. 终端 UI 架构
**优点**:
- React 组件化，可维护性强
- Hooks 模式，逻辑复用
- 响应式更新

**可借鉴到 BobQuant Streamlit**:
- 组件化设计
- 状态管理优化
- 实时刷新机制

### 4. 权限系统
**优点**:
- 细粒度控制
- 通配符规则
- ML 分类器辅助

**可借鉴到 BobQuant**:
```python
class PermissionSystem:
    def check_trade_permission(self, code, action, amount):
        # 检查风控规则
        # 检查用户配置
        # 返回是否允许
        pass
```

---

## 📈 与 BobQuant 对比

| 维度 | Claude Code | BobQuant |
|------|-------------|----------|
| **代码规模** | 512K 行 | ~230KB (新增) |
| **运行时** | Bun | Python |
| **UI** | React+Ink | Streamlit+Plotly |
| **工具数** | ~40 | ~20 |
| **命令数** | ~85 | ~15 |
| **架构复杂度** | 极高 | 中等 |

---

## 🎯 学习收获

### 1. 架构设计
- **管道模式**: 清晰的数据流
- **工具系统**: 自包含、可扩展
- **状态管理**: React Context + Store

### 2. 工程实践
- **Feature Flags**: 渐进式发布
- **Lazy Loading**: 延迟加载大模块
- **TypeScript Strict**: 类型安全

### 3. 用户体验
- **权限透明**: 用户清楚知道会发生什么
- **成本追踪**: 实时显示 token 消耗
- **错误处理**: 自动重试 + 友好提示

---

## 📚 后续学习方向

1. **深入研究 QueryEngine.ts** - LLM 交互核心
2. **学习工具系统设计** - 可扩展的工具架构
3. **借鉴权限系统** - 细粒度的权限控制
4. **优化 BobQuant 架构** - 应用学到的模式

---

**学习完成时间**: 2026-04-11  
**下一步**: 将学到的架构模式应用到 BobQuant 优化中
