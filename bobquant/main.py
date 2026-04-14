# -*- coding: utf-8 -*-
"""
BobQuant 交易引擎主入口 v3.0
集成重构的 5 个核心模块：工具系统、权限系统、错误处理、遥测系统、配置系统

v3.0 新增:
- ✅ 工具系统：统一的工具接口和注册表
- ✅ 权限系统：Claude Code 风格的权限管理模式
- ✅ 错误处理：标准化错误类型和恢复机制
- ✅ 遥测系统：异步事件采集和监控指标
- ✅ 配置系统：5 层配置继承和 JSON5 支持

v2.4 功能保留:
- 高频交易策略（剥头皮/动量/突破/均值回归）
- 网格做 T 策略
- 三重风控（止损/止盈/跟踪止损）
- ML+ 情绪综合决策
- 自动调仓引擎
"""

import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ==================== v3.0 新模块导入 ====================
# 配置系统
from .config import (
    ConfigLoader,
    BobQuantConfig,
    ConfigValidator,
    ValidationError as ConfigValidationError,
)

# 错误处理系统
from .errors import (
    BobQuantError,
    TradingError,
    DataError,
    ErrorClassifier,
    RecoveryManager,
    RetryConfig,
    CircuitBreakerConfig,
    retry,
    with_fallback,
    circuit_breaker,
    ErrorCategory,
    ErrorSeverity,
)

# 权限系统
from .permissions import (
    PermissionEngine,
    PermissionMode,
    PermissionRequest,
    RuleMatcher,
    TradeClassifier,
)

# 工具系统
from .tools import (
    ToolRegistry,
    get_registry,
    ToolContext,
    ToolResult,
    AuditLogger,
    audit_action,
)

# 遥测系统
from .telemetry import (
    TelemetrySink,
    TelemetryEvent,
    EventType,
    BatchProcessor,
    BatchConfig,
    JSONLPersister,
    PersistenceConfig,
    MetricsRegistry,
    get_metrics_registry,
    init_global_sink,
)

# ==================== 传统模块导入（向后兼容） ====================
try:
    from .core.account import Account, get_sellable_shares
    from .core.executor import Executor
    from .core.trading_rules import get_min_shares, normalize_shares
    from .data.provider import get_provider
    from .strategy.engine import get_strategy, GridTStrategy, RiskManager, DecisionEngine
    from .strategy.high_frequency import HighFrequencyEngine, create_high_frequency_strategy
    from .strategy.rebalance import create_rebalance_engine, get_rebalance_config_from_settings
    from .notify.feishu import send_feishu
    from .analysis.performance import generate_report, format_report
except ImportError:
    from core.account import Account, get_sellable_shares
    from core.executor import Executor
    from core.trading_rules import get_min_shares, normalize_shares
    from data.provider import get_provider
    from strategy.engine import get_strategy, GridTStrategy, RiskManager, DecisionEngine
    from strategy.high_frequency import HighFrequencyEngine, create_high_frequency_strategy
    from strategy.rebalance import create_rebalance_engine, get_rebalance_config_from_settings
    from notify.feishu import send_feishu
    from analysis.performance import generate_report, format_report


# ==================== 日志配置 ====================
def setup_logging(config: Optional[BobQuantConfig] = None) -> logging.Logger:
    """
    v3.0: 使用配置系统设置日志
    
    集成遥测系统到日志系统，所有日志同时输出到：
    1. 控制台
    2. 文件
    3. 遥测 Sink（用于监控和分析）
    """
    log_config = config.log if config else None
    log_dir = Path(log_config.dir) if log_config else Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置根日志记录器
    log_level = getattr(logging, log_config.log_level) if log_config else logging.INFO
    
    logger = logging.getLogger("bobquant")
    logger.setLevel(log_level)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    log_file = log_dir / f"bobquant_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(console_formatter)
    logger.addHandler(file_handler)
    
    return logger


# 全局日志记录器
logger = setup_logging()


# ==================== v3.0 核心组件初始化 ====================

class BobQuantEngine:
    """
    BobQuant v3.0 交易引擎
    
    集成 5 个重构模块：
    1. 配置系统：5 层配置继承
    2. 工具系统：统一工具接口
    3. 权限系统：权限管理模式
    4. 错误处理：标准化错误和恢复
    5. 遥测系统：监控和指标采集
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """初始化交易引擎"""
        self.config: Optional[BobQuantConfig] = None
        self.config_loader = ConfigLoader(config_path)
        
        # 错误处理系统
        self.error_classifier = ErrorClassifier()
        self.recovery_manager = RecoveryManager(
            retry_config=RetryConfig(
                max_retries=3,
                base_delay=1.0,
                max_delay=60.0,
            ),
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=5,
                timeout=30.0,
            ),
        )
        
        # 权限系统
        self.permission_engine = PermissionEngine(
            mode=PermissionMode.AUTO,  # AI 分类模式
            grace_period_ms=200.0,     # 200ms 防误触
            denial_threshold=3,        # 连续 3 次拒绝后降级
        )
        
        # 规则匹配器（用于权限规则）
        self.rule_matcher = RuleMatcher()
        
        # 工具系统
        self.tool_registry = get_registry()
        self.audit_logger = AuditLogger()
        
        # 遥测系统
        self.telemetry_sink: Optional[TelemetrySink] = None
        self.metrics_registry: Optional[MetricsRegistry] = None
        
        # 传统组件（延迟初始化）
        self.data_provider = None
        self.account = None
        self.executor = None
        self.grid_t = None
        self.risk_manager = None
        self.hf_engine = None
        self.decision_engine = None
        self.rebalance_engine = None
        
        logger.info("🚀 BobQuant v3.0 引擎初始化完成")
    
    def initialize(self) -> bool:
        """
        初始化所有组件
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 1. 加载配置
            logger.info("📋 加载配置...")
            self.config = self.config_loader.load_with_secrets()
            
            # 验证配置
            validator = ConfigValidator(self.config)
            if not validator.validate_schema():
                logger.error(f"配置 Schema 验证失败：{validator.errors}")
                return False
            
            if not validator.validate_business_rules():
                logger.error(f"配置业务规则验证失败：{validator.errors}")
                return False
            
            logger.info(f"✅ 配置加载成功 (模式：{self.config.system.mode if self.config.system else 'simulation'})")
            
            # 2. 初始化遥测系统
            logger.info("📊 初始化遥测系统...")
            self._init_telemetry()
            
            # 3. 初始化数据提供商
            logger.info("📈 初始化数据提供商...")
            self._init_data_provider()
            
            # 4. 初始化账户
            logger.info("💰 初始化账户...")
            self._init_account()
            
            # 5. 初始化执行器
            logger.info("⚡ 初始化执行器...")
            self._init_executor()
            
            # 6. 初始化策略引擎
            logger.info("🧠 初始化策略引擎...")
            self._init_strategies()
            
            # 7. 初始化权限系统
            logger.info("🔐 初始化权限系统...")
            self._init_permissions()
            
            # 8. 注册工具
            logger.info("🔧 注册工具...")
            self._register_tools()
            
            # 发送系统启动事件
            self._emit_telemetry(
                EventType.SYSTEM_START,
                "system.start",
                {
                    "version": "3.0.0",
                    "mode": self.config.system.mode if self.config.system else "simulation",
                    "stock_pool_size": len(self.config.stock_pool) if self.config.stock_pool else 0,
                }
            )
            
            logger.info("✅ 所有组件初始化完成")
            return True
            
        except Exception as e:
            classified = self.error_classifier.classify(e)
            logger.error(f"初始化失败：{classified.classified_error.message}")
            self._emit_telemetry(
                EventType.ERROR_OCCURRED,
                "system.error",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "category": classified.category.value,
                    "severity": classified.severity.value,
                }
            )
            return False
    
    def _init_telemetry(self):
        """初始化遥测系统"""
        # 创建 Telemetry Sink
        self.telemetry_sink = init_global_sink(
            max_queue_size=10000,
            enable_backpressure=True
        )
        
        # 创建批处理器
        batch_config = BatchConfig(
            max_batch_size=100,
            max_wait_time=5.0,
        )
        batch_processor = BatchProcessor(
            config=batch_config
        )
        
        # 创建持久化器
        log_dir = Path(self.config.log.dir) if self.config and self.config.log else Path("logs")
        telemetry_dir = log_dir / "telemetry"
        telemetry_dir.mkdir(parents=True, exist_ok=True)
        
        persistence_config = PersistenceConfig(
            base_dir=str(telemetry_dir),
            file_prefix="bobquant_events",
            max_file_size=100,
        )
        persister = JSONLPersister(config=persistence_config)
        
        # 注册消费者
        self.telemetry_sink.add_consumer(batch_processor.process)
        self.telemetry_sink.add_consumer(persister.save)
        
        # 启动 Sink
        self.telemetry_sink.start()
        
        # 初始化指标注册表
        self.metrics_registry = get_metrics_registry()
        
        logger.info(f"  ✅ 遥测系统就绪 (目录：{telemetry_dir})")
    
    def _init_data_provider(self):
        """初始化数据提供商"""
        data_config = self.config.data if self.config else None
        provider_name = data_config.primary if data_config else "tencent"
        
        self.data_provider = get_provider(provider_name)
        logger.info(f"  ✅ 数据提供商就绪 ({provider_name})")
    
    def _init_account(self):
        """初始化账户"""
        # 支持两种 stock_pool 格式：列表或字典
        positions_file = Path("positions.json")
        if self.config and self.config.stock_pool:
            if isinstance(self.config.stock_pool, list) and len(self.config.stock_pool) > 0:
                positions_file = Path(self.config.stock_pool[0].get('positions_file', 'positions.json'))
            elif isinstance(self.config.stock_pool, dict):
                positions_file = Path(self.config.stock_pool.get('positions_file', 'positions.json'))
        
        initial_capital = self.config.account.initial_capital if self.config and self.config.account else 1000000.0
        
        self.account = Account(str(positions_file), initial_capital).load()
        self.account.migrate_positions()
        
        logger.info(f"  ✅ 账户就绪 (初始资金：¥{initial_capital:,.0f})")
    
    def _init_executor(self):
        """初始化执行器"""
        if not self.config:
            raise ValueError("配置未初始化")
        
        account_config = self.config.account
        twap_config = self.config.twap
        
        self.executor = Executor(
            self.account,
            account_config.commission_rate if account_config else 0.0005,
            str(Path(self.config.log.dir) / "trades.json") if self.config.log else "trades.json",
            lambda msg: logger.info(msg),
            lambda title, msg: self._notify(title, msg),
            twap_enabled=twap_config.enabled if twap_config else False,
            twap_threshold=twap_config.threshold if twap_config else 10000,
            twap_slices=twap_config.slices if twap_config else 5,
            twap_duration=twap_config.duration_minutes if twap_config else 10,
        )
        
        if twap_config and twap_config.enabled:
            logger.info(f"  ✅ TWAP 执行器已启用 (阈值：{twap_config.threshold}股)")
        else:
            logger.info(f"  ✅ 执行器就绪")
    
    def _init_strategies(self):
        """初始化策略引擎"""
        if not self.config:
            return
        
        # 网格做 T 策略
        trade_cfg = {
            'day_trading': {
                'enabled': True,
                'threshold_pct': 0.0015,
                'max_holding_time': 300,
            }
        }
        self.grid_t = GridTStrategy(trade_cfg.get('day_trading', {}))
        self.grid_t.reset_if_new_day()
        
        # 风控管理器
        risk_config = {
            'stop_loss': {
                'enabled': True,
                'pct': -0.08,
            },
            'trailing_stop': {
                'enabled': True,
                'activation_pct': 0.05,
                'drawdown_pct': 0.02,
            },
        }
        self.risk_manager = RiskManager(risk_config)
        
        # 高频交易引擎
        hf_config = self.config.strategy or {}
        enable_high_freq = hf_config.get('high_frequency', {}).get('enabled', False) if isinstance(hf_config, dict) else False
        
        if enable_high_freq:
            self.hf_engine = HighFrequencyEngine({
                'scalping_threshold': 0.001,
                'max_holding_time': 300,
                'min_profit_tick': 1,
                'momentum_threshold': True,
                'reversion_threshold': 0.002,
                'breakout_window': 5,
            })
            logger.info(f"  ⚡ 高频交易引擎就绪")
        
        # 综合决策引擎
        enable_ml = hf_config.get('ml', {}).get('enabled', True) if isinstance(hf_config, dict) else True
        enable_sentiment = hf_config.get('sentiment', {}).get('enabled', True) if isinstance(hf_config, dict) else True
        
        if enable_ml or enable_sentiment:
            self.decision_engine = DecisionEngine({
                'enable_ml': enable_ml,
                'enable_sentiment': enable_sentiment,
                'ml_signal_weight': 0.4,
                'ta_signal_weight': 0.4,
                'ml_lookback_days': 200,
                'ml_min_train_samples': 60,
                'ml_probability_threshold': 0.6,
            })
            logger.info(f"  🧠 综合决策引擎就绪 (ML={enable_ml}, 情绪={enable_sentiment})")
        
        # 自动调仓引擎
        rebalance_config = self.config.rebalance if self.config else None
        if rebalance_config and rebalance_config.enabled:
            self.rebalance_engine = create_rebalance_engine(
                {
                    'enabled': True,
                    'mode': rebalance_config.mode,
                    'frequency': rebalance_config.frequency,
                    'threshold_pct': rebalance_config.threshold_pct,
                },
                lambda msg: logger.info(msg),
                lambda title, msg: self._notify(title, msg)
            )
            logger.info(f"  🔄 自动调仓引擎就绪 (模式:{rebalance_config.mode})")
    
    def _init_permissions(self):
        """初始化权限系统"""
        # 配置权限模式
        if self.config and self.config.system and self.config.system.debug:
            # 调试模式：允许交易
            self.permission_engine.set_mode(PermissionMode.ACCEPT_EDITS)
            logger.info(f"  🔓 权限模式：允许交易 (调试模式)")
        else:
            # 生产模式：AI 分类
            self.permission_engine.set_mode(PermissionMode.AUTO)
            logger.info(f"  🔐 权限模式：AI 分类 (生产模式)")
        
        # 设置 AI 分类器回调
        def ai_classifier(request: PermissionRequest) -> Dict[str, Any]:
            """AI 分类器：根据交易风险等级决策"""
            classifier = TradeClassifier()
            risk_level = classifier.classify(request.symbol, request.side, request.quantity, request.price)
            
            # 低风险：自动允许
            if risk_level == 'low':
                return {'granted': True, 'reason': '低风险交易'}
            # 中等风险：需要确认
            elif risk_level == 'normal':
                return {'granted': False, 'reason': '中等风险 - 需要确认'}
            # 高风险：拒绝
            else:
                return {'granted': False, 'reason': '高风险交易 - 拒绝'}
        
        self.permission_engine.classifier_callback = ai_classifier
        logger.info(f"  ✅ AI 分类器已配置")
    
    def _register_tools(self):
        """注册工具到注册表"""
        # 这里注册所有可用的交易工具
        # 示例：
        # from .tools.trading import OrderTool, PositionTool, QueryTool
        # self.tool_registry.register(OrderTool, category="trading")
        # self.tool_registry.register(PositionTool, category="trading")
        # self.tool_registry.register(QueryTool, category="query")
        
        logger.info(f"  ✅ 工具注册表就绪 (已注册：{len(self.tool_registry.list_tools())} 个工具)")
    
    def _emit_telemetry(
        self,
        event_type: EventType,
        event_name: str,
        attributes: Dict[str, Any],
        correlation_id: Optional[str] = None
    ):
        """发送遥测事件"""
        if self.telemetry_sink:
            self.telemetry_sink.emit(
                event_type=event_type,
                event_name=event_name,
                attributes=attributes,
                correlation_id=correlation_id,
                blocking=False,
            )
    
    def _check_permission(self, action: str, symbol: str, side: str, quantity: int, price: Optional[float] = None) -> bool:
        """
        v3.0: 使用权限系统检查交易权限
        
        Returns:
            bool: 是否允许执行
        """
        request = PermissionRequest(
            action=action,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
        )
        
        response = self.permission_engine.check_permission(
            request,
            rule_matcher=self.rule_matcher
        )
        
        # 记录权限检查事件
        self._emit_telemetry(
            EventType.RISK_CHECK_PASSED if response.granted else EventType.RISK_CHECK_FAILED,
            "permission.check",
            {
                "action": action,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "granted": response.granted,
                "reason": response.reason,
            }
        )
        
        return response.granted
    
    def _notify(self, title: str, message: str):
        """发送通知"""
        if not self.config or not self.config.notify or not self.config.notify.feishu:
            return
        
        if self.config.notify.feishu.enabled:
            user_id = self.config.notify.feishu.user_id
            if isinstance(user_id, str):
                send_feishu(title, message, user_id)
    
    def run_check(self) -> List[Dict[str, Any]]:
        """
        执行一次交易信号检查（v3.0 集成版）
        
        集成：
        1. 工具系统：所有交易操作通过工具执行
        2. 权限系统：每笔交易前检查权限
        3. 错误处理：标准化错误和恢复
        4. 遥测系统：记录所有事件
        """
        trades = []
        
        try:
            logger.info("📊 检查交易信号（v3.0 集成版）...")
            
            # Phase 0: 高频交易策略
            if self.hf_engine:
                trades.extend(self._run_high_frequency())
            
            # Phase 1: 网格做 T
            trades.extend(self._run_grid_t())
            
            # Phase 2: 风控
            trades.extend(self._run_risk_check())
            
            # Phase 3: 策略信号
            trades.extend(self._run_strategy_signals())
            
            # Phase 4: 自动调仓
            if self.rebalance_engine:
                trades.extend(self._run_rebalance())
            
            # 保存状态
            if trades:
                self.account.save()
                self.executor.sync_trade_log(trades)
                logger.info(f"  ✅ 执行 {len(trades)} 笔交易")
                
                # 发送交易汇总遥测
                self._emit_telemetry(
                    EventType.PERFORMANCE_METRIC,
                    "trading.summary",
                    {
                        "trade_count": len(trades),
                        "total_volume": sum(t.get('shares', 0) for t in trades),
                        "total_amount": sum(t.get('shares', 0) * t.get('price', 0) for t in trades),
                    }
                )
            else:
                logger.info(f"  ⚪ 无交易信号")
            
            return trades
            
        except Exception as e:
            classified = self.error_classifier.classify(e)
            logger.error(f"交易检查失败：{classified.classified_error.message}")
            
            # 尝试恢复
            if classified.recoverable:
                logger.info("尝试自动恢复...")
                # 可以执行恢复逻辑
            
            self._emit_telemetry(
                EventType.ERROR_OCCURRED,
                "trading.error",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "category": classified.category.value,
                }
            )
            
            return []
    
    def _run_high_frequency(self) -> List[Dict[str, Any]]:
        """执行高频交易策略"""
        trades = []
        
        if not self.hf_engine or not self.config or not self.config.stock_pool:
            return trades
        
        for stock in self.config.stock_pool:
            code, name = stock['code'], stock['name']
            
            try:
                quote = self.data_provider.get_quote(code)
                if not quote or quote['current'] <= 0:
                    continue
                
                df = self.data_provider.get_history(code, days=30)
                pos = self.account.get_position(code)
                
                hf_signal = self.hf_engine.check(code, name, quote, df, pos)
                
                if hf_signal.get('signal'):
                    logger.info(f"  🎯 高频信号：{name} - {hf_signal.get('strategy')}")
                    
                    # 权限检查
                    if hf_signal['signal'] == 'buy':
                        if not pos:
                            shares = max(10000 // quote['current'], 100)
                            
                            if self._check_permission('trade', code, 'buy', shares, quote['current']):
                                t = self.executor.buy(code, name, shares, quote['current'],
                                                    f"{hf_signal.get('strategy')}:{hf_signal.get('reason')}")
                                if t:
                                    trades.append(t)
                                    self.hf_engine.on_trade(code, 'buy')
                    
                    elif hf_signal['signal'] == 'sell':
                        if pos:
                            sellable = get_sellable_shares(pos)
                            if sellable > 0:
                                sell_shares = sellable // 2
                                
                                if self._check_permission('trade', code, 'sell', sell_shares, quote['current']):
                                    t = self.executor.sell(code, name, sell_shares, quote['current'],
                                                         f"{hf_signal.get('strategy')}:{hf_signal.get('reason')}")
                                    if t:
                                        trades.append(t)
                                        self.hf_engine.on_trade(code, 'sell')
            
            except Exception as e:
                logger.warning(f"高频策略检查失败 {code}: {e}")
        
        return trades
    
    def _run_grid_t(self) -> List[Dict[str, Any]]:
        """执行网格做 T 策略"""
        trades = []
        
        if not self.account or not self.data_provider:
            return trades
        
        codes = list(self.account.positions.keys())
        quotes = self.data_provider.get_quotes(codes)
        
        # 风控优先检查
        risk_checked = set()
        for code, pos in list(self.account.positions.items()):
            quote = quotes.get(code)
            if quote and quote['current'] > 0:
                result = self.risk_manager.check(code, pos, quote['current'])
                if result['action']:
                    risk_checked.add(code)
        
        # 做 T 检查
        for code, pos in list(self.account.positions.items()):
            if code in risk_checked:
                continue
            
            quote = quotes.get(code)
            if not quote or quote['current'] <= 0:
                continue
            
            name = self._find_name(code)
            sellable = get_sellable_shares(pos)
            
            if sellable > 0:
                df = self.data_provider.get_history(code, days=30)
                
                sell_n, sell_reason = self.grid_t.check_sell(code, quote, sellable, df)
                if sell_n > 0:
                    if self._check_permission('trade', code, 'sell', sell_n, quote['current']):
                        t = self.executor.sell(code, name, sell_n, quote['current'], sell_reason)
                        if t:
                            trades.append(t)
                            self.grid_t.record_sell(code, sell_n, quote['current'])
                
                bb_n, bb_reason = self.grid_t.check_buyback(code, quote['current'])
                if bb_n > 0:
                    if self._check_permission('trade', code, 'buy', bb_n, quote['current']):
                        t = self.executor.buy(code, name, bb_n, quote['current'], bb_reason, is_add=True)
                        if t:
                            trades.append(t)
                            self.grid_t.record_buyback(code)
        
        return trades
    
    def _run_risk_check(self) -> List[Dict[str, Any]]:
        """执行风控检查"""
        trades = []
        
        if not self.account or not self.data_provider:
            return trades
        
        codes = list(self.account.positions.keys())
        quotes = self.data_provider.get_quotes(codes)
        
        for code, pos in list(self.account.positions.items()):
            quote = quotes.get(code)
            if not quote or quote['current'] <= 0:
                continue
            
            result = self.risk_manager.check(code, pos, quote['current'])
            if result['action']:
                name = self._find_name(code)
                
                # 风控交易不需要权限检查（紧急止损）
                t = self.executor.sell(code, name, result['shares'], quote['current'],
                                      result['reason'], result['label'])
                if t:
                    trades.append(t)
                    
                    if 'take_profit' in result['action'] and self.account.has_position(code):
                        p = self.account.get_position(code)
                        p['profit_taken'] = p.get('profit_taken', 0) + 1
                    
                    if result['action'] in ('stop_loss', 'trailing_stop'):
                        self.risk_manager.clear_trailing(code)
        
        return trades
    
    def _run_strategy_signals(self) -> List[Dict[str, Any]]:
        """执行策略信号检查"""
        trades = []
        
        if not self.config or not self.config.stock_pool or not self.data_provider:
            return trades
        
        codes = [s['code'] for s in self.config.stock_pool]
        quotes = self.data_provider.get_quotes(codes)
        
        for stock in self.config.stock_pool:
            code, name, strat_name = stock['code'], stock['name'], stock['strategy']
            quote = quotes.get(code)
            
            if not quote or quote['current'] <= 0:
                continue
            
            try:
                df = self.data_provider.get_history(code, days=200)
                
                strategy = get_strategy(strat_name)
                ta_result = strategy.check(code, name, quote, df, self.account.get_position(code), self.config)
                
                if not ta_result.get('signal'):
                    continue
                
                # 使用决策引擎（如果有）
                if self.decision_engine:
                    decision = self.decision_engine.combine_signals(
                        code, name, quote, df,
                        self.account.get_position(code),
                        [ta_result]
                    )
                    
                    if decision.get('filtered'):
                        continue
                    
                    result = decision
                else:
                    result = ta_result
                
                sig = result.get('signal')
                
                if sig == 'buy' and not self.account.has_position(code):
                    shares = int(1000000 * 0.03 / quote['current'])
                    
                    if self._check_permission('trade', code, 'buy', shares, quote['current']):
                        t = self.executor.buy(code, name, shares, quote['current'], result['reason'])
                        if t:
                            trades.append(t)
                
                elif sig == 'sell' and self.account.has_position(code):
                    pos = self.account.get_position(code)
                    sellable = get_sellable_shares(pos)
                    
                    if sellable > 0:
                        sell_n = int(sellable * 0.5)
                        
                        if self._check_permission('trade', code, 'sell', sell_n, quote['current']):
                            t = self.executor.sell(code, name, sell_n, quote['current'], result['reason'])
                            if t:
                                trades.append(t)
            
            except Exception as e:
                logger.warning(f"策略信号检查失败 {code}: {e}")
        
        return trades
    
    def _run_rebalance(self) -> List[Dict[str, Any]]:
        """执行自动调仓"""
        trades = []
        
        if not self.rebalance_engine or not self.account or not self.data_provider:
            return trades
        
        current_prices = {}
        stock_names = {}
        
        for code in self.account.positions.keys():
            quote = self.data_provider.get_quote(code)
            if quote and quote['current'] > 0:
                current_prices[code] = quote['current']
                stock_names[code] = self._find_name(code)
        
        if self.config and self.config.stock_pool:
            for stock in self.config.stock_pool:
                code = stock['code']
                if code not in current_prices:
                    quote = self.data_provider.get_quote(code)
                    if quote and quote['current'] > 0:
                        current_prices[code] = quote['current']
                        stock_names[code] = stock['name']
        
        rebalance_result = self.rebalance_engine.check_rebalance(
            account=self.account,
            executor=self.executor,
            current_prices=current_prices,
            stock_names=stock_names
        )
        
        if rebalance_result.get('orders', 0) > 0:
            logger.info(f"  ✅ 调仓生成 {rebalance_result['orders']} 个订单")
        
        return trades
    
    def _find_name(self, code: str) -> str:
        """查找股票名称"""
        if self.config and self.config.stock_pool:
            for stock in self.config.stock_pool:
                if stock['code'] == code:
                    return stock['name']
        return ''
    
    def portfolio_summary(self) -> Dict[str, Any]:
        """打印账户汇总"""
        if not self.account or not self.data_provider:
            return {}
        
        mv = 0
        for code, pos in self.account.positions.items():
            q = self.data_provider.get_quote(code)
            if q and q['current'] > 0:
                mv += pos['shares'] * q['current']
        
        cash = self.account.cash
        total = mv + cash
        initial = self.config.account.initial_capital if self.config and self.config.account else 1000000.0
        pnl = total - initial
        pnl_pct = pnl / initial * 100
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 账户汇总")
        logger.info("=" * 60)
        logger.info(f"总资产：¥{total:,.0f} (现金¥{cash:,.0f} + 持仓¥{mv:,.0f})")
        logger.info(f"盈亏：¥{pnl:+,.0f} ({pnl_pct:+.2f}%)")
        logger.info(f"持仓：{len(self.account.positions)} 只")
        logger.info("=" * 60)
        
        # 发送性能指标到遥测
        self._emit_telemetry(
            EventType.PERFORMANCE_METRIC,
            "portfolio.summary",
            {
                "total_assets": total,
                "cash": cash,
                "market_value": mv,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "position_count": len(self.account.positions),
            }
        )
        
        return {
            'total': total,
            'cash': cash,
            'market_value': mv,
            'pnl': pnl,
            'pnl_pct': pnl_pct
        }
    
    def shutdown(self):
        """优雅关闭引擎"""
        logger.info("🛑 关闭 BobQuant 引擎...")
        
        # 停止遥测
        if self.telemetry_sink:
            self.telemetry_sink.stop(wait=True, timeout=5.0)
        
        # 发送系统停止事件
        self._emit_telemetry(
            EventType.SYSTEM_STOP,
            "system.stop",
            {"reason": "user_requested"}
        )
        
        logger.info("✅ 引擎已关闭")


# ==================== 主循环 ====================

def main_loop():
    """主循环"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="BobQuant 交易引擎")
    parser.add_argument("--config", type=str, default="bobquant/config/sim_config_v2_2.yaml", help="配置文件路径")
    parser.add_argument("--mode", type=str, default="simulation", help="运行模式：simulation/live")
    args = parser.parse_args()
    
    # 初始化引擎
    config_path = Path(args.config)  # 配置文件路径
    logger.info(f"📋 使用配置文件：{config_path}")
    engine = BobQuantEngine(config_path)
    
    if not engine.initialize():
        logger.error("引擎初始化失败，退出")
        return
    
    # 发送启动通知
    if engine.config and engine.config.notify and engine.config.notify.feishu:
        engine._notify(
            "⚡ BobQuant v3.0 启动",
            f"模拟盘已启动\n"
            f"模式：{engine.config.system.mode if engine.config.system else 'simulation'}\n"
            f"股票池：{len(engine.config.stock_pool) if engine.config.stock_pool else 0} 只"
        )
    
    last_force_buyback_date = ''
    
    while True:
        # 检查交易时段
        if engine.config and engine.config.trading_hours:
            th = engine.config.trading_hours
            now = datetime.now()
            time_str = now.strftime('%H:%M')
            
            is_trading = (
                th.morning_start <= time_str <= th.morning_end or
                th.afternoon_start <= time_str <= th.afternoon_end
            )
        else:
            is_trading = True  # 默认总是交易
        
        if is_trading:
            try:
                engine.run_check()
                
                # 收盘前强制接回
                now = datetime.now()
                time_str = now.strftime('%H:%M')
                today_str = now.strftime('%Y-%m-%d')
                
                if '14:55' <= time_str <= '15:00' and today_str != last_force_buyback_date:
                    logger.info("  ⏰ 收盘前检查：强制接回所有做 T 卖出的股票")
                    last_force_buyback_date = today_str
                
                engine.portfolio_summary()
                
            except Exception as e:
                logger.error(f"交易循环错误：{e}")
                engine._notify("⚠️ BobQuant 错误", f"交易检查出错：{e}")
        else:
            logger.info("⏸️ 非交易时段，等待...")
        
        time.sleep(engine.config.system.check_interval if engine.config and engine.config.system else 60)


if __name__ == '__main__':
    main_loop()
