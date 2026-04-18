#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易规则模块 - A 股交易规则实现
包括交易时间控制、T+1 规则、节假日判断等
"""

import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class TradingConfig:
    """
    交易配置 (2026 年 4 月最新版)
    
    依据：沪深北交易所交易规则 (2026 年修订征求意见稿)
    """
    # ============== 交易费用 ==============
    commission_rate: float = 0.0003  # 佣金率 (万三，最高 3‰)
    min_commission: float = 5.0  # 最低佣金 (元)
    stamp_duty: float = 0.0005  # 印花税 0.5‰ (万分之五，仅卖出)
    transfer_fee: float = 0.00001  # 过户费 0.01‰ (十万分之一)
    slippage: float = 0.001  # 滑点 (0.1%)
    
    # ============== 交易单位 ==============
    min_quantity_main: int = 100  # 主板最小买入数量 (1 手=100 股)
    quantity_step_main: int = 100  # 主板数量步长
    min_quantity_kcb: int = 200  # 科创板最小买入数量 (200 股起步)
    quantity_step_kcb: int = 100  # 科创板数量步长 (200 股整数倍)
    price_decimal: int = 2  # 价格小数位
    amount_decimal: int = 2  # 金额小数位
    max_order_quantity: int = 1000000  # 单笔最大申报 100 万股
    
    # ============== 涨跌停限制 ==============
    price_limit_main: float = 0.10  # 沪深主板 ±10%
    price_limit_st: float = 0.05  # ST/*ST ±5% (拟调整为 10%)
    price_limit_kcb: float = 0.20  # 科创板 ±20%
    price_limit_cyb: float = 0.20  # 创业板 ±20%
    price_limit_bse: float = 0.30  # 北交所 ±30%
    
    # ============== 临时停牌规则 ==============
    halt_threshold_1: float = 0.30  # 首次临停阈值 ±30%
    halt_threshold_2: float = 0.60  # 二次临停阈值 ±60%
    halt_duration: int = 10  # 临停时长 (分钟)


class TradingTimeController:
    """
    交易时间控制器 (2026 年最新版)
    
    A 股交易时间:
    - 开盘集合竞价：09:15 - 09:25 (确定开盘价)
    - 早盘连续竞价：09:30 - 11:30
    - 午盘连续竞价：13:00 - 14:57
    - 收盘集合竞价：14:57 - 15:00 (确定收盘价)
    - 盘后固定价格：15:05 - 15:30 (科创板/创业板，拟扩展至全部 A 股)
    
    注意：
    - 09:25-09:30 可提交申报，暂存券商系统，待 9:30 后报交易所
    - 11:30-13:00 可提交申报，暂存券商系统，待 13:00 后报交易所
    """
    
    # 交易时段定义
    CALL_AUCTION_OPEN_START = time(9, 15)   # 开盘集合竞价开始
    CALL_AUCTION_OPEN_END = time(9, 25)     # 开盘集合竞价结束
    MORNING_START = time(9, 30)             # 早盘连续竞价开始
    MORNING_END = time(11, 30)              # 早盘连续竞价结束
    AFTERNOON_START = time(13, 0)           # 午盘连续竞价开始
    AFTERNOON_CONTINUOUS_END = time(14, 57) # 连续竞价结束
    CALL_AUCTION_CLOSE_END = time(15, 0)    # 收盘集合竞价结束
    AFTER_HOURS_START = time(15, 5)         # 盘后固定价格开始
    AFTER_HOURS_END = time(15, 30)          # 盘后固定价格结束
    
    def __init__(self, holiday_file: str = None):
        """
        初始化交易时间控制器
        
        Args:
            holiday_file: 节假日文件路径 (JSON 格式)
        """
        if holiday_file is None:
            holiday_file = "/home/openclaw/.openclaw/workspace/config/holidays.json"
        
        self.holiday_file = Path(holiday_file)
        self.holidays = self._load_holidays()
        
        logger.info("交易时间控制器初始化完成")
    
    def _load_holidays(self) -> set:
        """加载节假日数据"""
        if self.holiday_file.exists():
            try:
                with open(self.holiday_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                holidays = set(data.get('holidays', []))
                logger.info(f"加载 {len(holidays)} 个节假日")
                return holidays
            except Exception as e:
                logger.error(f"加载节假日失败：{e}")
        
        # 默认节假日 (2026 年)
        default_holidays = {
            # 元旦
            '2026-01-01',
            # 春节
            '2026-02-17', '2026-02-18', '2026-02-19', 
            '2026-02-20', '2026-02-21', '2026-02-22', '2026-02-23',
            # 清明
            '2026-04-05', '2026-04-06', '2026-04-07',
            # 劳动节
            '2026-05-01', '2026-05-02', '2026-05-03',
            # 端午
            '2026-06-19', '2026-06-20', '2026-06-21',
            # 中秋 + 国庆
            '2026-09-25', '2026-09-26', '2026-09-27',
            '2026-10-01', '2026-10-02', '2026-10-03',
            '2026-10-04', '2026-10-05', '2026-10-06', '2026-10-07', '2026-10-08',
        }
        
        # 保存到文件
        try:
            self.holiday_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.holiday_file, 'w', encoding='utf-8') as f:
                json.dump({'holidays': list(default_holidays)}, f, indent=2)
            logger.info("已创建默认节假日文件")
        except Exception as e:
            logger.error(f"保存节假日文件失败：{e}")
        
        return default_holidays
    
    def is_trading_day(self, date: datetime = None) -> bool:
        """
        判断是否为交易日
        
        Args:
            date: 日期 (默认今天)
        
        Returns:
            True=交易日，False=非交易日
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime('%Y-%m-%d')
        
        # 检查节假日
        if date_str in self.holidays:
            return False
        
        # 检查周末
        if date.weekday() >= 5:  # 周六=5, 周日=6
            return False
        
        return True
    
    def is_trading_time(self, check_time: time = None) -> Tuple[bool, str]:
        """
        判断当前是否在交易时间内
        
        Args:
            check_time: 检查的时间 (默认当前时间)
        
        Returns:
            (是否交易时间，时段描述)
        """
        if check_time is None:
            check_time = datetime.now().time()
        
        # 开盘集合竞价 (09:15-09:25)
        if self.CALL_AUCTION_OPEN_START <= check_time <= self.CALL_AUCTION_OPEN_END:
            return True, "开盘集合竞价"
        
        # 早盘连续竞价 (09:30-11:30)
        if self.MORNING_START <= check_time <= self.MORNING_END:
            return True, "早盘连续竞价"
        
        # 午盘连续竞价 (13:00-14:57)
        if self.AFTERNOON_START <= check_time <= self.AFTERNOON_CONTINUOUS_END:
            return True, "午盘连续竞价"
        
        # 收盘集合竞价 (14:57-15:00)
        if self.AFTERNOON_CONTINUOUS_END < check_time <= self.CALL_AUCTION_CLOSE_END:
            return True, "收盘集合竞价"
        
        # 盘后固定价格 (15:05-15:30) - 仅科创板/创业板，拟扩展至全部 A 股
        if self.AFTER_HOURS_START <= check_time <= self.AFTER_HOURS_END:
            return True, "盘后固定价格"
        
        # 申报暂存时段 (09:25-09:30)
        if self.CALL_AUCTION_OPEN_END < check_time < self.MORNING_START:
            return False, "申报暂存 (09:25-09:30)"
        
        # 午休 (11:30-13:00)
        if self.MORNING_END < check_time < self.AFTERNOON_START:
            return False, "午休"
        
        # 盘前
        if check_time < self.CALL_AUCTION_OPEN_START:
            return False, "盘前"
        
        # 盘后
        if check_time > self.CALL_AUCTION_CLOSE_END:
            return False, "盘后"
        
        return False, "未知"
    
    def can_trade(self, dt: datetime = None) -> Tuple[bool, str]:
        """
        综合判断是否可以交易
        
        Args:
            dt: 日期时间 (默认当前)
        
        Returns:
            (是否可以交易，原因)
        """
        if dt is None:
            dt = datetime.now()
        
        # 检查是否交易日
        if not self.is_trading_day(dt):
            return False, "非交易日"
        
        # 检查是否交易时间
        is_time, period = self.is_trading_time(dt.time())
        if not is_time:
            return False, f"非交易时间 ({period})"
        
        return True, f"交易时间 ({period})"
    
    def next_trading_time(self, from_dt: datetime = None) -> datetime:
        """
        计算下一个交易时间
        
        Args:
            from_dt: 起始时间 (默认当前)
        
        Returns:
            下一个交易时间
        """
        if from_dt is None:
            from_dt = datetime.now()
        
        dt = from_dt
        
        # 如果当前是交易日且还在交易时间内，返回当前
        can, _ = self.can_trade(dt)
        if can:
            return dt
        
        # 如果还在交易日但已过交易时间，返回下一个交易日开盘
        if self.is_trading_day(dt.date()):
            next_dt = dt.replace(hour=9, minute=30, second=0, microsecond=0)
            if next_dt <= dt:
                # 已经过了今天开盘时间，找下一个交易日
                dt = dt + timedelta(days=1)
            else:
                return next_dt
        
        # 找下一个交易日
        while not self.is_trading_day(dt.date()):
            dt = dt + timedelta(days=1)
        
        return dt.replace(hour=9, minute=30, second=0, microsecond=0)
    
    def get_trading_periods(self, date: datetime = None) -> List[Dict]:
        """
        获取指定日期的交易时段
        
        Args:
            date: 日期
        
        Returns:
            交易时段列表
        """
        if date is None:
            date = datetime.now()
        
        if not self.is_trading_day(date):
            return []
        
        return [
            {"name": "开盘集合竞价", "start": "09:15", "end": "09:25", "type": "call_auction", "description": "确定开盘价"},
            {"name": "申报暂存", "start": "09:25", "end": "09:30", "type": "pending", "description": "可申报，暂存券商"},
            {"name": "早盘连续竞价", "start": "09:30", "end": "11:30", "type": "continuous", "description": "连续撮合"},
            {"name": "午休", "start": "11:30", "end": "13:00", "type": "break", "description": "可申报，暂存券商"},
            {"name": "午盘连续竞价", "start": "13:00", "end": "14:57", "type": "continuous", "description": "连续撮合"},
            {"name": "收盘集合竞价", "start": "14:57", "end": "15:00", "type": "call_auction", "description": "确定收盘价"},
            {"name": "盘后固定价格", "start": "15:05", "end": "15:30", "type": "after_hours", "description": "科创板/创业板 (拟扩展)"}
        ]


class TradingRules:
    """
    交易规则管理器
    
    实现 A 股交易规则:
    - T+1 交易
    - 涨跌停限制
    - 手续费计算
    - 订单验证
    """
    
    def __init__(self, config: TradingConfig = None):
        """
        初始化交易规则
        
        Args:
            config: 交易配置
        """
        self.config = config or TradingConfig()
        self.time_controller = TradingTimeController()
        
        # T+1 持仓记录 {stock_code: {buy_date: quantity}}
        self.t1_positions: Dict[str, Dict[str, int]] = {}
        
        logger.info("交易规则管理器初始化完成")
    
    def calculate_cost(self, price: float, quantity: int, 
                       is_buy: bool = True, board: str = "main") -> Dict[str, float]:
        """
        计算交易成本 (2026 年最新标准)
        
        费用构成:
        - 佣金：不超过 3‰，最低 5 元/笔 (买卖双向)
        - 印花税：0.5‰ (万分之五，仅卖出)
        - 过户费：0.01‰ (十万分之一，买卖双向)
        
        Args:
            price: 成交价格
            quantity: 成交数量
            is_buy: 是否买入
            board: 板块 (main/STAR/chiNext)
        
        Returns:
            成本明细
        """
        amount = price * quantity
        
        # 佣金 (万三，最低 5 元)
        commission = amount * self.config.commission_rate
        commission = max(commission, self.config.min_commission)
        
        # 过户费 (十万分之一，双向)
        transfer_fee = amount * self.config.transfer_fee
        
        # 印花税 (万分之五，仅卖出)
        stamp_duty = amount * self.config.stamp_duty if not is_buy else 0
        
        # 总成本 (不含滑点)
        total_cost = commission + transfer_fee + stamp_duty
        
        # 滑点成本
        slippage_cost = amount * self.config.slippage
        
        return {
            "amount": round(amount, self.config.amount_decimal),
            "commission": round(commission, self.config.amount_decimal),
            "transfer_fee": round(transfer_fee, self.config.amount_decimal),
            "stamp_duty": round(stamp_duty, self.config.amount_decimal),
            "slippage": round(slippage_cost, self.config.amount_decimal),
            "total_cost": round(total_cost + slippage_cost, self.config.amount_decimal),
            "total_cost_no_slippage": round(total_cost, self.config.amount_decimal),
            "net_amount": round(amount + total_cost if is_buy else amount - total_cost, 
                               self.config.amount_decimal),
            "fee_rate": f"{total_cost/amount*10000:.2f}‱" if amount > 0 else "0‱"
        }
    
    def get_board_type(self, stock_code: str) -> str:
        """
        判断股票所属板块
        
        Args:
            stock_code: 股票代码
        
        Returns:
            板块类型 (main/STAR/chiNext/bse/st)
        """
        code = stock_code[:3] if len(stock_code) >= 3 else stock_code
        
        # 科创板 (688 开头)
        if stock_code.startswith('688'):
            return 'STAR'
        
        # 创业板 (300/301 开头)
        if code in ['300', '301']:
            return 'chiNext'
        
        # 北交所 (8/4/9 开头)
        if code in ['871', '872', '873', '430', '920']:
            return 'bse'
        
        # ST/*ST
        if 'ST' in stock_code.upper():
            return 'st'
        
        # 默认主板
        return 'main'
    
    def validate_order(self, stock_code: str, action: str, 
                       price: float, quantity: int, 
                       position: Dict = None, prev_close: float = None) -> Tuple[bool, str]:
        """
        验证订单合法性 (2026 年最新规则)
        
        Args:
            stock_code: 股票代码
            action: buy/sell
            price: 价格
            quantity: 数量
            position: 当前持仓信息
            prev_close: 昨收价 (用于涨跌停检查)
        
        Returns:
            (是否合法，错误信息)
        """
        board = self.get_board_type(stock_code)
        
        # ============== 检查数量 ==============
        if board == 'STAR':
            # 科创板：200 股起步，200 股整数倍
            if quantity < self.config.min_quantity_kcb:
                return False, f"科创板最小买入 200 股"
            if quantity < 200:
                return False, "科创板买入须为 200 股整数倍"
            if (quantity - 200) % 100 != 0:
                return False, "科创板买入须为 200 股整数倍"
        else:
            # 主板/创业板：100 股起步，100 股整数倍
            if quantity < self.config.min_quantity_main:
                return False, f"最小买入 100 股 (1 手)"
            if quantity % self.config.quantity_step_main != 0:
                return False, "买入须为 100 股整数倍"
        
        # 单笔最大申报
        if quantity > self.config.max_order_quantity:
            return False, f"单笔申报最大 {self.config.max_order_quantity} 股"
        
        # ============== 检查价格 ==============
        if price <= 0:
            return False, "价格必须大于 0"
        
        # 价格精度
        price_str = str(price)
        if '.' in price_str and len(price_str.split('.')[1]) > self.config.price_decimal:
            return False, f"价格最多保留 {self.config.price_decimal} 位小数"
        
        # 涨跌停检查
        if prev_close and prev_close > 0:
            valid, reason = self.check_price_limit(stock_code, price, prev_close, board)
            if not valid:
                return False, reason
        
        # ============== 卖出检查 ==============
        if action == "sell":
            if not position:
                return False, "无持仓"
            
            available = position.get('available', 0)
            if quantity > available:
                return False, f"可卖数量不足 (可用：{available})"
            
            # 卖出时不足 100 股须一次性卖出
            if position.get('quantity', 0) < 100:
                if quantity != position.get('quantity', 0):
                    return False, "余额不足 100 股须一次性卖出"
        
        # ============== 检查交易时间 ==============
        can_trade, reason = self.time_controller.can_trade()
        if not can_trade:
            # 允许在申报暂存时段提交
            if "申报暂存" in reason:
                return True, f"申报暂存 ({reason})"
            return False, f"禁止交易：{reason}"
        
        return True, "验证通过"
    
    def record_buy(self, stock_code: str, quantity: int, buy_date: str = None):
        """
        记录买入 (用于 T+1)
        
        Args:
            stock_code: 股票代码
            quantity: 数量
            buy_date: 买入日期 (默认今天)
        """
        if buy_date is None:
            buy_date = datetime.now().strftime('%Y-%m-%d')
        
        if stock_code not in self.t1_positions:
            self.t1_positions[stock_code] = {}
        
        if buy_date not in self.t1_positions[stock_code]:
            self.t1_positions[stock_code][buy_date] = 0
        
        self.t1_positions[stock_code][buy_date] += quantity
        logger.info(f"记录买入：{stock_code} {quantity}股 @ {buy_date}")
    
    def get_available_quantity(self, stock_code: str, 
                                total_position: int) -> int:
        """
        计算可卖数量 (考虑 T+1)
        
        Args:
            stock_code: 股票代码
            total_position: 总持仓
        
        Returns:
            可卖数量
        """
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 计算今日买入的数量 (不可卖)
        locked_quantity = 0
        if stock_code in self.t1_positions:
            for date, qty in self.t1_positions[stock_code].items():
                if date >= today:  # 今日及以后买入的不可卖
                    locked_quantity += qty
        
        # 清理过期记录 (昨天的今天可以卖了)
        if stock_code in self.t1_positions:
            expired_dates = [d for d in self.t1_positions[stock_code].keys() 
                           if d < yesterday]
            for d in expired_dates:
                del self.t1_positions[stock_code][d]
        
        available = total_position - locked_quantity
        return max(0, available)
    
    def check_price_limit(self, stock_code: str, price: float, 
                          prev_close: float, board: str = None) -> Tuple[bool, str]:
        """
        检查涨跌停限制 (2026 年最新版)
        
        板块涨跌幅:
        - 沪深主板：±10%
        - ST/*ST: ±5% (拟调整为 10%)
        - 科创板/创业板：±20%
        - 北交所：±30%
        - 新股上市前 5 日：无限制
        
        Args:
            stock_code: 股票代码
            price: 申报价格
            prev_close: 昨收价
            board: 板块类型 (可选)
        
        Returns:
            (是否合法，错误信息)
        """
        if prev_close <= 0:
            return True, "无昨收价参考"
        
        if board is None:
            board = self.get_board_type(stock_code)
        
        # 获取板块涨跌幅限制
        if board == 'st':
            limit = self.config.price_limit_st
            board_name = "ST/*ST"
        elif board == 'STAR':
            limit = self.config.price_limit_kcb
            board_name = "科创板"
        elif board == 'chiNext':
            limit = self.config.price_limit_cyb
            board_name = "创业板"
        elif board == 'bse':
            limit = self.config.price_limit_bse
            board_name = "北交所"
        else:
            limit = self.config.price_limit_main
            board_name = "主板"
        
        # 计算涨跌停价
        upper_limit = prev_close * (1 + limit)
        lower_limit = prev_close * (1 - limit)
        
        if price > upper_limit:
            return False, f"超过{board_name}涨停价 {upper_limit:.2f} (+{limit*100:.0f}%)"
        
        if price < lower_limit:
            return False, f"低于{board_name}跌停价 {lower_limit:.2f} (-{limit*100:.0f}%)"
        
        return True, f"价格在{board_name}涨跌停范围内 (±{limit*100:.0f}%)"
    
    def check_temporary_halt(self, stock_code: str, price: float, 
                              open_price: float) -> Tuple[bool, str]:
        """
        检查临时停牌 (无涨跌幅限制股票)
        
        触发条件:
        - 较开盘价首次上涨/下跌达 30% → 临停 10 分钟
        - 较开盘价首次上涨/下跌达 60% → 临停 10 分钟
        
        Args:
            stock_code: 股票代码
            price: 当前价
            open_price: 开盘价
        
        Returns:
            (是否临停，临停信息)
        """
        if open_price <= 0:
            return False, ""
        
        change_pct = abs(price - open_price) / open_price
        
        if change_pct >= self.config.halt_threshold_2:
            return True, f"触发二次临停 (±60%), 停牌{self.config.halt_duration}分钟"
        
        if change_pct >= self.config.halt_threshold_1:
            return True, f"触发首次临停 (±30%), 停牌{self.config.halt_duration}分钟"
        
        return False, ""
    
    def get_status(self) -> Dict:
        """获取规则状态"""
        can_trade, reason = self.time_controller.can_trade()
        return {
            "can_trade": can_trade,
            "reason": reason,
            "trading_periods": self.time_controller.get_trading_periods(),
            "config": {
                "commission_rate": f"{self.config.commission_rate*10000:.1f}‱ (万{self.config.commission_rate*10000:.0f})",
                "stamp_duty": f"{self.config.stamp_duty*10000:.1f}‱ (万分之{self.config.stamp_duty*10000:.0f})",
                "transfer_fee": f"{self.config.transfer_fee*100000:.2f}‱ (十万分之{self.config.transfer_fee*100000:.1f})",
                "min_commission": self.config.min_commission,
                "price_limits": {
                    "main": f"±{self.config.price_limit_main*100:.0f}%",
                    "st": f"±{self.config.price_limit_st*100:.0f}%",
                    "STAR/chiNext": f"±{self.config.price_limit_kcb*100:.0f}%",
                    "bse": f"±{self.config.price_limit_bse*100:.0f}%"
                }
            },
            "t1_locked_stocks": len(self.t1_positions)
        }


# 全局单例
_global_rules: Optional[TradingRules] = None

def get_trading_rules() -> TradingRules:
    """获取全局交易规则单例"""
    global _global_rules
    if _global_rules is None:
        _global_rules = TradingRules()
    return _global_rules


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    rules = TradingRules()
    
    # 测试交易时间
    can, reason = rules.time_controller.can_trade()
    print(f"当前可交易：{can} ({reason})")
    
    # 测试成本计算
    cost = rules.calculate_cost(100.00, 100, is_buy=True)
    print(f"买入成本：{cost}")
    
    cost = rules.calculate_cost(100.00, 100, is_buy=False)
    print(f"卖出成本：{cost}")
    
    # 测试 T+1
    rules.record_buy("600519", 100)
    available = rules.get_available_quantity("600519", 100)
    print(f"可卖数量：{available} (应该为 0，因为 T+1)")
    
    print(f"规则状态：{rules.get_status()}")
