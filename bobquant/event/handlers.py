# -*- coding: utf-8 -*-
"""
BobQuant 事件处理器实现

提供各类事件的处理器实现，包括:
- 风控处理器 (紧急止损/止盈)
- 通知处理器 (异步发送飞书通知)
- 日志处理器 (记录事件日志)
- 信号处理器 (处理交易信号)

使用示例:
    from bobquant.event.handlers import RiskHandler, NotifyHandler
    
    # 创建处理器实例
    risk_handler = RiskHandler(executor, account)
    notify_handler = NotifyHandler(user_id)
    
    # 注册到事件引擎
    engine.register(EVENT_RISK_TRIGGERED, risk_handler.handle)
    engine.register(EVENT_NOTIFY, notify_handler.handle)
"""
import logging
from datetime import datetime
from typing import Optional, Any, Dict

from ..event.engine import Event, EVENT_RISK_TRIGGERED, EVENT_NOTIFY, EVENT_SIGNAL_GENERATED, EVENT_LOG


class RiskHandler:
    """
    风控事件处理器
    
    处理紧急风控事件 (止损、止盈、移动止损)，立即执行风控操作。
    适用于需要即时响应的场景，不等待轮询周期。
    
    使用示例:
        handler = RiskHandler(executor, account, data_provider)
        engine.register(EVENT_RISK_TRIGGERED, handler.handle)
    """
    
    def __init__(self, executor, account, data_provider=None):
        """
        初始化风控处理器
        
        Args:
            executor: 交易执行器 (Executor 实例)
            account: 账户对象 (Account 实例)
            data_provider: 数据提供者 (可选，用于获取实时价格)
        """
        self.executor = executor
        self.account = account
        self.data_provider = data_provider
        self._log_prefix = "[RiskHandler]"
    
    def handle(self, event: Event) -> None:
        """
        处理风控事件
        
        Args:
            event: 风控事件对象，data 应包含:
                - code: 股票代码
                - action: 风控动作 ('stop_loss', 'take_profit', 'trailing_stop')
                - reason: 触发原因
                - shares: 涉及股数 (可选，为 0 时自动计算)
                - timestamp: 时间戳 (可选，自动设置)
        """
        if event.type != EVENT_RISK_TRIGGERED:
            return
        
        # 设置时间戳
        event.data['timestamp'] = datetime.now()
        
        code = event.data.get('code', '')
        action = event.data.get('action', '')
        reason = event.data.get('reason', '')
        shares = event.data.get('shares', 0)
        
        if not code:
            logging.error(f"{self._log_prefix} 风控事件缺少股票代码")
            return
        
        if not self.account.has_position(code):
            logging.warning(f"{self._log_prefix} {code} 无持仓，忽略风控事件")
            return
        
        # 获取实时价格
        price = self._get_current_price(code)
        if price <= 0:
            logging.error(f"{self._log_prefix} 无法获取 {code} 实时价格")
            return
        
        # 获取持仓信息
        pos = self.account.get_position(code)
        if shares <= 0:
            # 未指定股数，使用可卖股数
            from ..core.account import get_sellable_shares
            shares = get_sellable_shares(pos)
        
        # 确定风控标签
        label_map = {
            'stop_loss': '🔴 止损',
            'take_profit': '🟢 止盈',
            'trailing_stop': '🟡 移动止损'
        }
        label = label_map.get(action, '⚠️ 风控')
        
        # 执行卖出
        name = pos.get('name', code)
        try:
            trade = self.executor.sell(code, name, shares, price, reason, label)
            if trade:
                logging.info(f"{self._log_prefix} ✅ 风控执行成功：{code} {action} {shares}股 @ ¥{price:.2f}")
                
                # 更新账户
                self.account.save()
            else:
                logging.error(f"{self._log_prefix} ❌ 风控执行失败：{code}")
        except Exception as e:
            logging.error(f"{self._log_prefix} ❌ 风控执行异常：{e}")
    
    def _get_current_price(self, code: str) -> float:
        """
        获取实时价格
        
        Args:
            code: 股票代码
        
        Returns:
            float: 当前价格，获取失败返回 0
        """
        if self.data_provider:
            try:
                quote = self.data_provider.get_quote(code)
                if quote:
                    return quote.get('current', 0)
            except Exception as e:
                logging.error(f"{self._log_prefix} 获取价格失败：{e}")
        
        return 0


class NotifyHandler:
    """
    通知事件处理器
    
    异步发送飞书通知，不阻塞主循环。
    适用于非紧急的通知场景。
    
    使用示例:
        handler = NotifyHandler(user_id)
        engine.register(EVENT_NOTIFY, handler.handle)
    """
    
    def __init__(self, user_id: str = ''):
        """
        初始化通知处理器
        
        Args:
            user_id: 飞书用户 ID
        """
        self.user_id = user_id
        self._log_prefix = "[NotifyHandler]"
    
    def handle(self, event: Event) -> None:
        """
        处理通知事件
        
        Args:
            event: 通知事件对象，data 应包含:
                - title: 通知标题
                - message: 通知内容
                - timestamp: 时间戳 (可选，自动设置)
        """
        if event.type != EVENT_NOTIFY:
            return
        
        # 设置时间戳
        event.data['timestamp'] = datetime.now()
        
        title = event.data.get('title', '通知')
        message = event.data.get('message', '')
        
        if not message:
            logging.warning(f"{self._log_prefix} 通知内容为空")
            return
        
        try:
            # 异步发送通知 (实际实现时应使用异步调用)
            self._send_notify(title, message)
            logging.info(f"{self._log_prefix} ✅ 通知发送成功：{title}")
        except Exception as e:
            logging.error(f"{self._log_prefix} ❌ 通知发送失败：{e}")
    
    def _send_notify(self, title: str, message: str) -> None:
        """
        发送通知
        
        Args:
            title: 通知标题
            message: 通知内容
        """
        # TODO: 实际实现时替换为真实的 send_feishu 调用
        # from notify.feishu import send_feishu
        # send_feishu(title, message, self.user_id)
        
        # 临时实现：打印日志
        logging.info(f"[飞书通知] {title}: {message}")


class SignalHandler:
    """
    信号事件处理器
    
    处理交易信号生成事件，记录信号并可选地自动执行。
    
    使用示例:
        handler = SignalHandler(strategy_engine, executor, account)
        engine.register(EVENT_SIGNAL_GENERATED, handler.handle)
    """
    
    def __init__(self, strategy_engine=None, executor=None, account=None, auto_execute: bool = False):
        """
        初始化信号处理器
        
        Args:
            strategy_engine: 策略引擎 (可选)
            executor: 交易执行器 (可选)
            account: 账户对象 (可选)
            auto_execute: 是否自动执行信号 (默认 False)
        """
        self.strategy_engine = strategy_engine
        self.executor = executor
        self.account = account
        self.auto_execute = auto_execute
        self._log_prefix = "[SignalHandler]"
    
    def handle(self, event: Event) -> None:
        """
        处理信号事件
        
        Args:
            event: 信号事件对象，data 应包含:
                - code: 股票代码
                - name: 股票名称
                - signal: 信号类型 ('buy', 'sell')
                - reason: 信号原因
                - strength: 信号强度 ('normal', 'strong', 'weak')
                - timestamp: 时间戳 (可选，自动设置)
        """
        if event.type != EVENT_SIGNAL_GENERATED:
            return
        
        # 设置时间戳
        event.data['timestamp'] = datetime.now()
        
        code = event.data.get('code', '')
        name = event.data.get('name', '')
        signal = event.data.get('signal', '')
        reason = event.data.get('reason', '')
        strength = event.data.get('strength', 'normal')
        
        if not code or not signal:
            logging.warning(f"{self._log_prefix} 信号事件缺少必要字段")
            return
        
        # 记录信号
        logging.info(f"{self._log_prefix} 📊 信号：{name}({code}) {signal} - {reason} [{strength}]")
        
        # 记录到策略引擎 (如果有)
        if self.strategy_engine:
            try:
                self.strategy_engine.record_signal(code, signal, reason, strength)
            except Exception as e:
                logging.error(f"{self._log_prefix} 记录信号失败：{e}")
        
        # 自动执行 (如果启用)
        if self.auto_execute and self.executor and self.account:
            self._execute_signal(code, name, signal, reason, strength)
    
    def _execute_signal(self, code: str, name: str, signal: str, 
                        reason: str, strength: str) -> None:
        """
        执行交易信号
        
        Args:
            code: 股票代码
            name: 股票名称
            signal: 信号类型
            reason: 信号原因
            strength: 信号强度
        """
        # TODO: 实现信号自动执行逻辑
        logging.info(f"{self._log_prefix} ⚠️ 自动执行信号功能尚未实现")


class LogHandler:
    """
    日志事件处理器
    
    处理 EVENT_LOG 类型事件，记录到日志文件。
    可作为通用处理器使用，记录所有事件。
    
    使用示例:
        handler = LogHandler(log_file='events.log')
        engine.register(EVENT_LOG, handler.handle)
        # 或作为通用处理器
        engine.register_general(handler.handle)
    """
    
    def __init__(self, log_file: Optional[str] = None, level: int = logging.INFO):
        """
        初始化日志处理器
        
        Args:
            log_file: 日志文件路径 (可选，不指定则使用默认日志)
            level: 日志级别
        """
        self.log_file = log_file
        self.level = level
        self._log_prefix = "[LogHandler]"
        
        # 如果指定了文件，创建独立的 logger
        if log_file:
            self.logger = logging.getLogger('EventLog')
            self.logger.setLevel(level)
            
            # 添加文件处理器
            handler = logging.FileHandler(log_file, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
            self.logger.addHandler(handler)
        else:
            self.logger = logging
    
    def handle(self, event: Event) -> None:
        """
        处理日志事件
        
        Args:
            event: 日志事件对象，data 应包含:
                - message: 日志消息
                - level: 日志级别 (可选)
                - timestamp: 时间戳 (可选，自动设置)
        """
        if event.type == EVENT_LOG:
            message = event.data.get('message', str(event.data))
            level = event.data.get('level', self.level)
            self.logger.log(level, message)
        else:
            # 记录其他类型事件
            self.logger.info(f"[Event] {event.type}: {event.data}")


class EventHandler:
    """
    通用事件处理器
    
    将事件处理委托给自定义回调函数。
    适用于需要灵活处理逻辑的场景。
    
    使用示例:
        def my_handler(event):
            print(f"收到事件：{event.type}")
        
        handler = EventHandler(my_handler)
        engine.register(EVENT_SIGNAL_GENERATED, handler.handle)
    """
    
    def __init__(self, callback, event_types: Optional[list] = None):
        """
        初始化通用事件处理器
        
        Args:
            callback: 回调函数 (接收 Event 对象)
            event_types: 监听的事件类型列表 (可选，None 表示所有类型)
        """
        self.callback = callback
        self.event_types = event_types
        self._log_prefix = "[EventHandler]"
    
    def handle(self, event: Event) -> None:
        """
        处理事件
        
        Args:
            event: 事件对象
        """
        # 检查事件类型
        if self.event_types and event.type not in self.event_types:
            return
        
        try:
            self.callback(event)
        except Exception as e:
            logging.error(f"{self._log_prefix} 回调执行失败：{e}")


# ============ 便捷函数 ============

def create_risk_handler(executor, account, data_provider=None) -> RiskHandler:
    """
    创建风控处理器的便捷函数
    
    Args:
        executor: 交易执行器
        account: 账户对象
        data_provider: 数据提供者
    
    Returns:
        RiskHandler: 风控处理器实例
    """
    return RiskHandler(executor, account, data_provider)


def create_notify_handler(user_id: str = '') -> NotifyHandler:
    """
    创建通知处理器的便捷函数
    
    Args:
        user_id: 飞书用户 ID
    
    Returns:
        NotifyHandler: 通知处理器实例
    """
    return NotifyHandler(user_id)


def create_signal_handler(strategy_engine=None, executor=None, account=None, 
                          auto_execute: bool = False) -> SignalHandler:
    """
    创建信号处理器的便捷函数
    
    Args:
        strategy_engine: 策略引擎
        executor: 交易执行器
        account: 账户对象
        auto_execute: 是否自动执行
    
    Returns:
        SignalHandler: 信号处理器实例
    """
    return SignalHandler(strategy_engine, executor, account, auto_execute)
