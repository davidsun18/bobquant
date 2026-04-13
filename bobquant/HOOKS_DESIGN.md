# BobQuant Hooks 系统设计指南

## 🎯 从 Claude Code 借鉴的架构模式

本文档详细说明如何将 Claude Code 的 Hooks 系统应用到 BobQuant 量化交易系统中。

---

## 1. 权限控制系统

### 1.1 交易权限 Hook

```typescript
// src/hooks/useCanExecuteTrade.ts
import { useCallback } from 'react'
import type { Strategy, Position, Order } from '../types/trading'
import type { PermissionDecision } from '../types/permissions'

type TradeContext = {
  strategy: Strategy
  order: Order
  accountBalance: number
  currentPosition?: Position
  marketStatus: 'open' | 'closed' | 'auction'
}

type CanExecuteTradeFn = (
  context: TradeContext
) => Promise<PermissionDecision>

export function useCanExecuteTrade(): CanExecuteTradeFn {
  const config = useTradingConfig()
  const riskLimits = useRiskLimits()
  
  return useCallback(async (context: TradeContext) => {
    // 1. 检查市场状态
    if (context.marketStatus === 'closed') {
      return {
        behavior: 'deny',
        reason: '市场已关闭',
        riskLevel: 'low'
      }
    }
    
    // 2. 检查资金限制
    const requiredCapital = context.order.quantity * context.order.price
    if (requiredCapital > context.accountBalance * config.maxCapitalRatio) {
      return {
        behavior: 'deny',
        reason: '超出资金限制',
        riskLevel: 'high'
      }
    }
    
    // 3. 检查持仓限制
    if (context.currentPosition) {
      const totalPosition = context.currentPosition.quantity + context.order.quantity
      if (totalPosition > config.maxPositionSize) {
        return {
          behavior: 'ask',
          description: `持仓将达到 ${totalPosition} 股，超过建议的 ${config.maxPositionSize} 股`,
          riskLevel: 'medium'
        }
      }
    }
    
    // 4. 检查策略权限
    if (!config.enabledStrategies.includes(context.strategy.id)) {
      return {
        behavior: 'deny',
        reason: '策略未启用',
        riskLevel: 'low'
      }
    }
    
    // 5. 通过检查
    return {
      behavior: 'allow',
      riskLevel: 'low'
    }
  }, [config, riskLimits])
}
```

### 1.2 权限决策类型

```typescript
// src/types/permissions.ts
export type PermissionDecision<T = any> = 
  | { 
      behavior: 'allow'
      updatedInput?: T
      riskLevel: 'low' | 'medium' | 'high'
    }
  | { 
      behavior: 'deny'
      reason: string
      riskLevel: 'low' | 'medium' | 'high'
      suggestion?: string
    }
  | { 
      behavior: 'ask'
      description: string
      riskLevel: 'low' | 'medium' | 'high'
      confirmText?: string
      cancelText?: string
    }

export type PermissionMode = 
  | 'dontAsk'      // 自动模式
  | 'askForHigh'   // 高风险时询问
  | 'askAlways'    // 总是询问
```

### 1.3 权限上下文

```typescript
// src/context/PermissionContext.ts
export type PermissionContext = {
  mode: PermissionMode
  alwaysAllowRules: {
    session: string[]      // 会话级规则
    global: string[]       // 全局规则
  }
  riskLimits: {
    maxSingleTrade: number
    maxDailyLoss: number
    maxPositionValue: number
  }
}

// 使用 Hook
const permissionContext = usePermissionContext()
```

---

## 2. 策略插件系统

### 2.1 策略插件接口

```typescript
// src/types/strategy-plugin.ts
export interface StrategyPlugin {
  name: string
  version: string
  description: string
  author: string
  
  // 策略定义
  strategies: StrategyDefinition[]
  
  // 技术指标
  indicators: IndicatorDefinition[]
  
  // 钩子函数
  hooks: {
    onBeforeTrade?: (ctx: TradeContext) => Promise<HookResult>
    onAfterTrade?: (ctx: TradeContext) => Promise<void>
    onRiskCheck?: (ctx: RiskContext) => Promise<boolean>
    onMarketOpen?: () => Promise<void>
    onMarketClose?: () => Promise<void>
    onSignal?: (signal: TradingSignal) => Promise<TradingAction | null>
  }
  
  // 配置项
  config?: PluginConfig
}

export interface HookResult {
  pass: boolean
  message?: string
  suggestions?: string[]
  blockTrade?: boolean
}
```

### 2.2 插件管理 Hook

```typescript
// src/hooks/useManageStrategyPlugins.ts
import { useCallback, useEffect } from 'react'
import { loadAllPlugins } from '../utils/plugins/pluginLoader'
import { loadStrategyPlugins } from '../utils/plugins/loadStrategyPlugins'
import { loadIndicatorPlugins } from '../utils/plugins/loadIndicatorPlugins'

export function useManageStrategyPlugins() {
  const setAppState = useSetAppState()
  
  const loadPlugins = useCallback(async () => {
    try {
      // 1. 加载所有插件
      const { enabled, disabled, errors } = await loadAllPlugins()
      
      // 2. 加载策略
      const strategies = await loadStrategyPlugins(enabled)
      
      // 3. 加载指标
      const indicators = await loadIndicatorPlugins(enabled)
      
      // 4. 注册钩子
      for (const plugin of enabled) {
        if (plugin.hooks) {
          registerPluginHooks(plugin)
        }
      }
      
      // 5. 更新状态
      setAppState(prev => ({
        ...prev,
        plugins: {
          ...prev.plugins,
          strategies,
          indicators,
          errors: [...prev.plugins.errors, ...errors]
        }
      }))
      
    } catch (error) {
      console.error('Failed to load plugins:', error)
    }
  }, [setAppState])
  
  useEffect(() => {
    loadPlugins()
  }, [])
  
  return { loadPlugins }
}
```

### 2.3 会话钩子管理

```typescript
// src/utils/hooks/sessionHooks.ts
export type TradingHookEvent = 
  | 'before-market-open'
  | 'after-market-close'
  | 'before-trade'
  | 'after-trade'
  | 'on-signal'
  | 'on-risk-check'
  | 'on-stop-loss'
  | 'on-take-profit'

export type FunctionHookCallback = (
  context: any,
  signal?: AbortSignal
) => boolean | Promise<boolean>

export type FunctionHook = {
  type: 'function'
  id: string
  event: TradingHookEvent
  matcher: string  // 策略匹配模式
  callback: FunctionHookCallback
  timeout: number
  errorMessage: string
}

export function addTradingHook(
  sessionId: string,
  event: TradingHookEvent,
  matcher: string,
  callback: FunctionHookCallback,
  options?: { timeout?: number, id?: string }
): string {
  const id = options?.id || `hook-${Date.now()}-${Math.random()}`
  const hook: FunctionHook = {
    type: 'function',
    id,
    event,
    matcher,
    callback,
    timeout: options?.timeout || 5000,
    errorMessage: 'Hook execution failed'
  }
  
  // 添加到会话钩子注册表
  addHookToSession(sessionId, event, hook)
  return id
}

export function removeTradingHook(
  sessionId: string,
  hookId: string
): void {
  removeHookFromSession(sessionId, hookId)
}
```

---

## 3. 输入处理系统

### 3.1 交易命令输入

```typescript
// src/hooks/useTradingInput.ts
import { useCallback, useState, useRef } from 'react'
import { useDoublePress } from './useDoublePress'

type TradingInputProps = {
  value: string
  onChange: (value: string) => void
  onSubmit: (command: TradingCommand) => void
  onExit: () => void
  suggestions: TradingSuggestion[]
  focus?: boolean
}

export function useTradingInput({
  value,
  onChange,
  onSubmit,
  onExit,
  suggestions,
  focus = true
}: TradingInputProps): TradingInputState {
  const [cursor, setCursor] = useState(0)
  const [selectedSuggestion, setSelectedSuggestion] = useState(-1)
  const historyRef = useRef<TradingCommand[]>([])
  const historyIndexRef = useRef(-1)
  
  // 双按 Ctrl-C 退出
  const handleCtrlC = useDoublePress(
    show => {
      if (show) {
        showNotification('再次按下 Ctrl-C 退出')
      }
    },
    () => onExit()
  )
  
  // 处理命令提交
  const handleSubmit = useCallback(() => {
    const command = parseTradingCommand(value)
    if (command) {
      onSubmit(command)
      historyRef.current.push(command)
      historyIndexRef.current = historyRef.current.length
      onChange('')
    }
  }, [value, onSubmit])
  
  // 历史记录导航
  const handleHistoryUp = useCallback(() => {
    if (historyIndexRef.current > 0) {
      historyIndexRef.current--
      const cmd = historyRef.current[historyIndexRef.current]
      onChange(serializeCommand(cmd))
    }
  }, [])
  
  const handleHistoryDown = useCallback(() => {
    if (historyIndexRef.current < historyRef.current.length - 1) {
      historyIndexRef.current++
      const cmd = historyRef.current[historyIndexRef.current]
      onChange(serializeCommand(cmd))
    } else {
      historyIndexRef.current = historyRef.current.length
      onChange('')
    }
  }, [])
  
  // 建议选择
  const handleSuggestionSelect = useCallback((index: number) => {
    setSelectedSuggestion(index)
    if (index >= 0 && suggestions[index]) {
      onChange(suggestions[index].text)
    }
  }, [suggestions])
  
  return {
    value,
    cursor,
    selectedSuggestion,
    suggestions,
    onChange,
    onSubmit: handleSubmit,
    onHistoryUp: handleHistoryUp,
    onHistoryDown: handleHistoryDown,
    onSuggestionSelect: handleSuggestionSelect,
    onCtrlC: handleCtrlC
  }
}
```

### 3.2 交易命令类型

```typescript
// src/types/trading-commands.ts
export type TradingCommand =
  | { type: 'buy'; symbol: string; quantity: number; price?: number }
  | { type: 'sell'; symbol: string; quantity: number; price?: number }
  | { type: 'hold'; symbol: string }
  | { type: 'query'; symbol: string }
  | { type: 'strategy'; action: 'start' | 'stop' | 'status'; name: string }
  | { type: 'risk'; action: 'set'; limit: string; value: number }
  | { type: 'custom'; raw: string }

export function parseTradingCommand(input: string): TradingCommand | null {
  const parts = input.trim().split(/\s+/)
  const [action, symbol, quantity, price] = parts
  
  switch (action.toLowerCase()) {
    case 'buy':
    case 'b':
      return {
        type: 'buy',
        symbol: symbol?.toUpperCase() || '',
        quantity: parseInt(quantity) || 0,
        price: price ? parseFloat(price) : undefined
      }
    case 'sell':
    case 's':
      return {
        type: 'sell',
        symbol: symbol?.toUpperCase() || '',
        quantity: parseInt(quantity) || 0,
        price: price ? parseFloat(price) : undefined
      }
    // ... 其他命令
    default:
      return { type: 'custom', raw: input }
  }
}
```

---

## 4. 会话管理系统

### 4.1 交易会话状态

```typescript
// src/types/trading-session.ts
export type TradingSession = {
  id: string
  startTime: number
  endTime?: number
  status: 'active' | 'paused' | 'closed'
  
  // 策略状态
  strategies: Map<string, StrategyState>
  
  // 持仓
  positions: Map<string, Position>
  
  // 订单历史
  orders: Order[]
  
  // 会话钩子
  hooks: SessionHooksState
  
  // 远程桥接 (可选)
  bridge?: TradingBridge
  
  // 统计数据
  stats: {
    totalTrades: number
    profitLoss: number
    winRate: number
  }
}

export type StrategyState = {
  id: string
  name: string
  enabled: boolean
  lastSignal?: TradingSignal
  performance: {
    daily: number
    weekly: number
    monthly: number
  }
}
```

### 4.2 会话管理 Hook

```typescript
// src/hooks/useTradingSession.ts
import { useEffect, useCallback } from 'react'

export function useTradingSession(): TradingSessionContext {
  const session = useAppState(s => s.currentSession)
  const setAppState = useSetAppState()
  
  // 创建新会话
  const createSession = useCallback(() => {
    const newSession: TradingSession = {
      id: generateSessionId(),
      startTime: Date.now(),
      status: 'active',
      strategies: new Map(),
      positions: new Map(),
      orders: [],
      hooks: new Map(),
      stats: {
        totalTrades: 0,
        profitLoss: 0,
        winRate: 0
      }
    }
    
    setAppState(prev => ({
      ...prev,
      currentSession: newSession
    }))
    
    return newSession
  }, [setAppState])
  
  // 关闭会话
  const closeSession = useCallback(() => {
    if (!session) return
    
    setAppState(prev => ({
      ...prev,
      currentSession: {
        ...session,
        endTime: Date.now(),
        status: 'closed'
      }
    }))
  }, [session, setAppState])
  
  // 添加持仓
  const addPosition = useCallback((position: Position) => {
    if (!session) return
    
    setAppState(prev => ({
      ...prev,
      currentSession: {
        ...session,
        positions: new Map(session.positions).set(position.symbol, position)
      }
    }))
  }, [session, setAppState])
  
  // 添加订单
  const addOrder = useCallback((order: Order) => {
    if (!session) return
    
    setAppState(prev => ({
      ...prev,
      currentSession: {
        ...session,
        orders: [...session.orders, order],
        stats: {
          ...session.stats,
          totalTrades: session.stats.totalTrades + 1
        }
      }
    }))
  }, [session, setAppState])
  
  return {
    session,
    createSession,
    closeSession,
    addPosition,
    addOrder,
    isActive: session?.status === 'active'
  }
}
```

---

## 5. 通知系统

### 5.1 通知类型

```typescript
// src/types/notifications.ts
export type NotificationType = 
  | 'info'
  | 'success'
  | 'warning'
  | 'error'
  | 'trade'
  | 'risk'

export type NotificationPriority = 
  | 'low'
  | 'normal'
  | 'high'
  | 'immediate'

export interface Notification {
  key: string
  type: NotificationType
  message: string
  priority: NotificationPriority
  timeoutMs?: number
  action?: {
    label: string
    onClick: () => void
  }
  data?: any
}
```

### 5.2 通知 Hook

```typescript
// src/hooks/useTradingNotifications.ts
import { useCallback } from 'react'

export function useTradingNotifications() {
  const { addNotification, removeNotification } = useNotifications()
  
  // 交易执行通知
  const notifyTradeExecuted = useCallback((order: Order) => {
    addNotification({
      key: `trade-${order.id}`,
      type: 'success',
      message: `订单已执行：${order.side} ${order.quantity}股 ${order.symbol} @ ${order.price}`,
      priority: 'high',
      timeoutMs: 5000,
      data: order
    })
  }, [addNotification])
  
  // 风险警告通知
  const notifyRiskWarning = useCallback((warning: RiskWarning) => {
    addNotification({
      key: `risk-${warning.id}`,
      type: 'warning',
      message: warning.message,
      priority: 'immediate',
      timeoutMs: 10000,
      action: {
        label: '查看详情',
        onClick: () => showRiskDetails(warning)
      }
    })
  }, [addNotification])
  
  // 策略信号通知
  const notifyStrategySignal = useCallback((signal: TradingSignal) => {
    addNotification({
      key: `signal-${signal.id}`,
      type: 'info',
      message: `${signal.strategy} 发出 ${signal.action} 信号`,
      priority: 'normal',
      timeoutMs: 3000,
      data: signal
    })
  }, [addNotification])
  
  return {
    notifyTradeExecuted,
    notifyRiskWarning,
    notifyStrategySignal
  }
}
```

---

## 6. 快捷键系统

### 6.1 交易快捷键

```typescript
// src/hooks/useTradingKeybindings.ts
import { useKeybinding } from '../keybindings/useKeybinding'

export function useTradingKeybindings(handlers: TradingHandlers) {
  // 买入快捷键 (Ctrl+B)
  useKeybinding('trading:buy', handlers.handleBuy, {
    context: 'Trading'
  })
  
  // 卖出快捷键 (Ctrl+S)
  useKeybinding('trading:sell', handlers.handleSell, {
    context: 'Trading'
  })
  
  // 持仓查询 (Ctrl+P)
  useKeybinding('trading:positions', handlers.handlePositions, {
    context: 'Trading'
  })
  
  // 策略切换 (Ctrl+T)
  useKeybinding('trading:toggle-strategy', handlers.handleToggleStrategy, {
    context: 'Trading'
  })
  
  // 风险限制 (Ctrl+R)
  useKeybinding('trading:risk-limits', handlers.handleRiskLimits, {
    context: 'Trading'
  })
  
  // 紧急平仓 (Ctrl+X)
  useKeybinding('trading:emergency-close', handlers.handleEmergencyClose, {
    context: 'Trading'
  })
  
  // 全局：刷新数据 (F5)
  useKeybinding('app:refresh-data', handlers.handleRefresh, {
    context: 'Global'
  })
}
```

---

## 7. 异步任务管理

### 7.1 任务注册表

```typescript
// src/utils/hooks/tradingTaskRegistry.ts
export type PendingTradingTask = {
  taskId: string
  taskName: string
  taskType: 'order' | 'query' | 'analysis' | 'sync'
  startTime: number
  timeout: number
  progress: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: any
  error?: string
}

const pendingTasks = new Map<string, PendingTradingTask>()

export function registerTradingTask(task: PendingTradingTask): void {
  pendingTasks.set(task.taskId, task)
}

export function updateTaskProgress(taskId: string, progress: number): void {
  const task = pendingTasks.get(taskId)
  if (task) {
    task.progress = progress
  }
}

export function completeTask(taskId: string, result: any): void {
  const task = pendingTasks.get(taskId)
  if (task) {
    task.status = 'completed'
    task.result = result
  }
}

export function failTask(taskId: string, error: string): void {
  const task = pendingTasks.get(taskId)
  if (task) {
    task.status = 'failed'
    task.error = error
  }
}
```

### 7.2 任务轮询 Hook

```typescript
// src/hooks/useTaskPoller.ts
import { useEffect, useState } from 'react'

export function useTaskPoller(taskIds: string[], pollInterval = 1000) {
  const [tasks, setTasks] = useState<PendingTradingTask[]>([])
  
  useEffect(() => {
    const pollTasks = async () => {
      const updatedTasks = taskIds
        .map(id => pendingTasks.get(id))
        .filter((t): t is PendingTradingTask => t !== undefined)
      
      setTasks(updatedTasks)
      
      // 检查是否有未完成的任务
      const hasPending = updatedTasks.some(
        t => t.status === 'pending' || t.status === 'running'
      )
      
      if (!hasPending) {
        return // 所有任务完成，停止轮询
      }
    }
    
    pollTasks()
    const interval = setInterval(pollTasks, pollInterval)
    return () => clearInterval(interval)
  }, [taskIds, pollInterval])
  
  return tasks
}
```

---

## 8. 最佳实践总结

### 8.1 Hook 设计原则

1. **单一职责**: 每个 Hook 只做一件事
2. **组合优先**: 小 Hook 组合成大功能
3. **类型安全**: 完整的 TypeScript 类型定义
4. **错误处理**: 优雅降级，不中断整体流程
5. **性能优化**: 使用 useCallback、useMemo、useRef

### 8.2 状态管理模式

```typescript
// ✅ 推荐：集中式状态管理
const setAppState = useSetAppState()
setAppState(prev => ({
  ...prev,
  trading: {
    ...prev.trading,
    positions: new Map(...)
  }
}))

// ❌ 避免：分散的状态
const [positions, setPositions] = useState(...)
const [orders, setOrders] = useState(...)
const [strategies, setStrategies] = useState(...)
```

### 8.3 权限检查流程

```typescript
// 标准权限检查流程
async function checkPermission(context: TradeContext) {
  // 1. 快速失败检查
  if (marketClosed) return deny('市场关闭')
  
  // 2. 配置检查
  if (!config.enabled) return deny('功能未启用')
  
  // 3. 风险检查
  if (riskTooHigh) return ask('风险较高，确认继续？')
  
  // 4. 通过
  return allow()
}
```

### 8.4 错误处理模式

```typescript
// 独立错误处理，不中断整体流程
try {
  await loadStrategyPlugin(plugin)
} catch (error) {
  errors.push({
    type: 'plugin-error',
    source: plugin.name,
    message: error.message
  })
  // 继续加载其他插件
}
```

---

## 9. 实施路线图

### 第一阶段 (P0 - 核心功能)
- [ ] 实现 `useCanExecuteTrade` 权限 Hook
- [ ] 实现 `useTradingSession` 会话管理
- [ ] 实现 `useTradingNotifications` 通知系统
- [ ] 实现基础插件加载系统

### 第二阶段 (P1 - 增强功能)
- [ ] 实现 `useTradingInput` 输入处理
- [ ] 实现 `useTradingKeybindings` 快捷键
- [ ] 实现会话钩子系统
- [ ] 实现策略插件接口

### 第三阶段 (P2 - 高级功能)
- [ ] 实现远程会话桥接
- [ ] 实现异步任务管理
- [ ] 实现虚拟滚动 (大量数据展示)
- [ ] 实现自动补全/建议系统

---

*文档生成时间：2026-04-11*
*基于 Claude Code Hooks 系统分析*
