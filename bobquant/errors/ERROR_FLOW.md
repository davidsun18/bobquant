# BobQuant 错误分类与处理流程图

## 📊 错误分类流程

```mermaid
flowchart TD
    A[原始异常 Exception] --> B{ErrorClassifier}
    B --> C[规则匹配]
    C --> D{错误类型判断}
    
    D -->|网络相关 | E[NetworkError/TimeoutError/RateLimitError]
    D -->|认证相关 | F[AuthenticationError]
    D -->|数据相关 | G[DataError 子类]
    D -->|交易相关 | H[TradingError 子类]
    D -->|策略相关 | I[StrategyError 子类]
    D -->|系统相关 | J[SystemError 子类]
    D -->|外部服务 | K[ExternalServiceError]
    
    E --> L{严重程度评估}
    F --> L
    G --> L
    H --> L
    I --> L
    J --> L
    K --> L
    
    L -->|Critical| M[立即告警]
    L -->|High| N[需要处理]
    L -->|Medium| O[可稍后处理]
    L -->|Low| P[记录日志]
    
    M --> Q{可恢复？}
    N --> Q
    O --> Q
    P --> Q
    
    Q -->|是 | R[自动恢复策略]
    Q -->|否 | S[人工干预]
    
    R --> T[retry_with_backoff]
    R --> U[retry_immediately]
    R --> V[wait_and_retry]
    R --> W[reconfigure]
    
    S --> X[记录错误上下文]
    X --> Y[生成用户消息]
    Y --> Z[返回错误响应]
```

## 🔄 错误恢复流程

```mermaid
flowchart TD
    A[函数调用] --> B{熔断器状态}
    
    B -->|CLOSED| C[执行函数]
    B -->|OPEN| D[拒绝执行]
    B -->|HALF_OPEN| E[有限执行]
    
    D --> F[返回熔断错误]
    
    C --> G{执行结果}
    E --> G
    
    G -->|成功 | H[记录成功]
    G -->|失败 | I[记录失败]
    
    H --> J{熔断器状态}
    J -->|HALF_OPEN| K[成功计数 +1]
    K --> L{达到阈值？}
    L -->|是 | M[切换到 CLOSED]
    L -->|否 | N[保持 HALF_OPEN]
    J -->|CLOSED| O[重置失败计数]
    
    I --> P{熔断器状态}
    P -->|CLOSED| Q[失败计数 +1]
    Q --> R{达到阈值？}
    R -->|是 | S[切换到 OPEN]
    R -->|否 | T[保持 CLOSED]
    P -->|HALF_OPEN| U[切换到 OPEN]
    
    S --> V[启动超时计时器]
    V --> W{超时到达？}
    W -->|是 | X[切换到 HALF_OPEN]
    W -->|否 | Y[保持 OPEN]
```

## 📉 重试退避策略

```mermaid
flowchart LR
    A[第 1 次失败] --> B[延迟 1s]
    B --> C[第 2 次尝试]
    C -->|失败 | D[延迟 2s]
    D --> E[第 3 次尝试]
    E -->|失败 | F[延迟 4s]
    F --> G[第 4 次尝试]
    G -->|失败 | H[延迟 8s]
    H --> I[第 5 次尝试]
    I -->|失败 | J[放弃，抛出错误]
    
    C -->|成功 | K[返回结果]
    E -->|成功 | K
    G -->|成功 | K
    I -->|成功 | K
    
    style A fill:#ffcccc
    style J fill:#ff6666
    style K fill:#ccffcc
```

## 🔄 数据源故障转移流程

```mermaid
flowchart TD
    A[请求数据] --> B[尝试主数据源 #0]
    B --> C{成功？}
    
    C -->|是 | D[返回数据]
    C -->|失败 | E[记录失败]
    
    E --> F{有备用数据源？}
    F -->|是 | G[切换到 #1]
    F -->|否 | H[返回错误]
    
    G --> I{成功？}
    I -->|是 | D
    I -->|失败 | J[记录失败]
    
    J --> K{有备用数据源？}
    K -->|是 | L[切换到 #2]
    K -->|否 | H
    
    L --> M{成功？}
    M -->|是 | D
    M -->|否 | H
    
    D --> N[重置到主数据源]
```

## 🎯 错误处理决策树

```mermaid
flowchart TD
    A[捕获异常] --> B{是 BobQuantError?}
    
    B -->|是 | C[直接使用]
    B -->|否 | D[分类转换]
    
    D --> E{匹配规则？}
    E -->|是 | F[创建标准化错误]
    E -->|否 | G[创建通用 APIError]
    
    C --> H{可恢复？}
    F --> H
    G --> H
    
    H -->|是 | I[执行恢复策略]
    H -->|否 | J[生成用户消息]
    
    I --> K{恢复成功？}
    K -->|是 | L[返回结果]
    K -->|否 | M{达到最大重试？}
    
    M -->|是 | J
    M -->|否 | I
    
    J --> N[记录日志]
    N --> O[返回错误响应]
```

## 📋 错误类型层次结构

```
BobQuantError (基类)
│
├── APIError
│   ├── NetworkError
│   ├── TimeoutError
│   ├── RateLimitError
│   └── AuthenticationError
│
├── DataError
│   ├── DataNotFoundError
│   ├── DataFormatError
│   ├── DataValidationError
│   └── DataStaleError
│
├── TradingError
│   ├── OrderError
│   │   └── OrderRejectedError
│   ├── InsufficientFundsError
│   ├── PositionError
│   └── MarketClosedError
│
├── StrategyError
│   ├── SignalError
│   ├── ConfigurationError
│   └── BacktestError
│
├── SystemError
│   ├── FileSystemError
│   ├── DatabaseError
│   └── MemoryError
│
└── ExternalServiceError
    └── ThirdPartyAPIError
```

## 🔧 恢复策略选择

```mermaid
flowchart TD
    A[错误分类完成] --> B{错误类型}
    
    B -->|RateLimitError| C[retry_with_backoff]
    B -->|TimeoutError| C
    B -->|NetworkError| D[retry_immediately]
    B -->|DataStaleError| D
    B -->|MarketClosedError| E[wait_and_retry]
    B -->|AuthenticationError| F[reconfigure]
    B -->|ConfigurationError| F
    B -->|其他可恢复 | C
    
    C --> G[指数退避重试]
    D --> H[立即重试]
    E --> I[等待特定时间]
    F --> J[重新配置]
    
    G --> K{成功？}
    H --> K
    I --> K
    J --> K
    
    K -->|否 | L[manual_intervention]
    K -->|是 | M[返回结果]
```

## 📊 错误严重程度处理

```mermaid
flowchart TD
    A[错误发生] --> B{严重程度}
    
    B -->|Critical| C[立即告警]
    B -->|High| D[记录并通知]
    B -->|Medium| E[记录日志]
    B -->|Low| F[静默处理]
    
    C --> G[停止相关操作]
    C --> H[发送告警通知]
    C --> I[需要人工介入]
    
    D --> J[尝试自动恢复]
    D --> K[记录详细上下文]
    
    E --> L[标准日志记录]
    E --> M[可选重试]
    
    F --> N[最小化处理]
    F --> O[继续执行]
```

## 🎯 用户消息生成流程

```mermaid
flowchart TD
    A[BobQuantError] --> B{语言设置}
    
    B -->|zh| C[中文模板]
    B -->|en| D[英文模板]
    
    C --> E{详细程度}
    D --> E
    
    E -->|BRIEF| F[标题 + 简短消息]
    E -->|STANDARD| G[标题 + 消息 + 建议]
    E -->|DETAILED| H[标题 + 消息 + 建议 + 技术细节]
    
    F --> I[用户消息对象]
    G --> I
    H --> I
    
    I --> J{输出格式}
    J -->|string| K[文本格式]
    J -->|dict| L[JSON 格式]
    J -->|display| M[UI 展示]
```

## 📈 统计与监控

系统自动跟踪以下指标：

```
错误统计
├── 按分类统计 (by_category)
│   ├── network: 15
│   ├── data: 8
│   ├── trading: 3
│   └── system: 1
│
├── 按严重程度统计 (by_severity)
│   ├── critical: 2
│   ├── high: 10
│   ├── medium: 12
│   └── low: 3
│
├── 可恢复性统计
│   ├── recoverable: 20
│   └── non_recoverable: 7
│
└── 恢复成功率
    ├── retry_success_rate: 85%
    ├── fallback_success_rate: 92%
    └── circuit_breaker_trips: 3
```

---

**文档版本**: v1.0  
**最后更新**: 2026-04-11  
**灵感来源**: Claude Code 错误处理系统
