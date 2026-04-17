# -*- coding: utf-8 -*-
"""
BobQuant 配置中心
统一加载 yaml 配置，消除所有硬编码路径
"""
import os
import yaml
from pathlib import Path

# ==================== 路径自动探测 ====================
# 项目根目录 = 本文件所在的 bobquant/ 的父目录
_THIS_DIR = Path(__file__).resolve().parent          # bobquant/config/
PROJECT_ROOT = _THIS_DIR.parent                       # bobquant/
WORKSPACE_ROOT = PROJECT_ROOT.parent                  # quant_strategies/

# 关键目录（全部基于 PROJECT_ROOT 推导，零硬编码）
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "logs"
CORE_DIR = PROJECT_ROOT / "core"

# 兼容旧版：sim_trading 目录（过渡期仍使用）
SIM_TRADING_DIR = WORKSPACE_ROOT / "sim_trading"
SIM_TRADING_DIR.mkdir(parents=True, exist_ok=True)

# ==================== 配置文件路径 ====================
SETTINGS_FILE = CONFIG_DIR / "settings.yaml"
STOCK_POOL_FILE = CONFIG_DIR / "stock_pool.yaml"

# ==================== 运行时文件路径（基于配置推导） ====================
POSITIONS_FILE = SIM_TRADING_DIR / "account_ideal.json"
LOG_FILE = SIM_TRADING_DIR / "模拟盘日志.log"
TRADE_LOG_FILE = SIM_TRADING_DIR / "交易记录.json"
GUARD_LOG_FILE = SIM_TRADING_DIR / "guard.log"


def _load_yaml(filepath):
    """安全加载 yaml 文件"""
    fp = Path(filepath)
    if not fp.exists():
        raise FileNotFoundError(f"配置文件不存在: {fp}")
    with open(fp, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def _deep_get(d, keys, default=None):
    """嵌套字典取值: _deep_get(cfg, 'strategy.stop_loss_pct', -0.08)"""
    for key in keys.split('.'):
        if isinstance(d, dict):
            d = d.get(key, default)
        else:
            return default
    return d


class Settings:
    """全局配置单例"""
    _instance = None
    _settings = None
    _stock_pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, settings_file=None, stock_pool_file=None):
        """加载配置（支持覆盖默认路径）"""
        sf = Path(settings_file) if settings_file else SETTINGS_FILE
        spf = Path(stock_pool_file) if stock_pool_file else STOCK_POOL_FILE

        self._settings = _load_yaml(sf)
        self._stock_pool = _load_yaml(spf)
        return self

    @property
    def raw(self):
        """原始配置字典"""
        if self._settings is None:
            self.load()
        return self._settings

    def get(self, key_path, default=None):
        """获取配置值，支持点分路径: settings.get('strategy.stop_loss_pct')"""
        if self._settings is None:
            self.load()
        return _deep_get(self._settings, key_path, default)

    @property
    def stock_pool(self):
        """股票池列表: [{'code':'sh.601398', 'name':'工商银行', 'strategy':'bollinger'}, ...]"""
        if self._stock_pool is None:
            self.load()
        return self._stock_pool

    # ---- 快捷属性 ----
    @property
    def initial_capital(self):
        return self.get('account.initial_capital', 1000000)

    @property
    def commission_rate(self):
        return self.get('account.commission_rate', 0.0005)

    @property
    def check_interval(self):
        return self.get('system.check_interval', 30)

    @property
    def positions_file(self):
        return str(POSITIONS_FILE)

    @property
    def log_file(self):
        return str(LOG_FILE)

    @property
    def trade_log_file(self):
        return str(TRADE_LOG_FILE)

    def is_trading_hours(self):
        """判断当前是否在交易时段"""
        from datetime import datetime
        now = datetime.now()
        if now.weekday() >= 5:
            return False

        def _to_minutes(time_str):
            h, m = map(int, time_str.split(':'))
            return h * 60 + m

        t = now.hour * 60 + now.minute
        ms = _to_minutes(self.get('trading_hours.morning_start', '09:25'))
        me = _to_minutes(self.get('trading_hours.morning_end', '11:35'))
        as_ = _to_minutes(self.get('trading_hours.afternoon_start', '12:55'))
        ae = _to_minutes(self.get('trading_hours.afternoon_end', '15:05'))

        return (ms <= t <= me) or (as_ <= t <= ae)


# 全局单例
settings = Settings()


def get_settings():
    """获取全局配置实例"""
    return settings


# ==================== 向后兼容：生成旧版 CONFIG / TRADE_CONFIG ====================
def to_legacy_config():
    """生成旧版 CONFIG 字典（过渡期使用，逐步废弃）"""
    s = get_settings()
    cfg = s.raw

    CONFIG = {
        'initial_capital': s.initial_capital,
        'commission_rate': s.commission_rate,
        'positions_file': s.positions_file,
        'log_file': s.log_file,
        'trade_log_file': s.trade_log_file,
        'check_interval': s.check_interval,
        'feishu_push': s.get('notify.feishu.enabled', True),
        'user_id': s.get('notify.feishu.user_id', ''),
        'max_position_percent': s.get('account.max_position_pct', 0.08),
        'max_stocks': s.get('account.max_stocks', 20),
        'stock_pool': [(item['code'], item['name'], item['strategy']) for item in s.stock_pool],
    }

    TRADE_CONFIG = {
        'pyramid_levels': s.get('strategy.pyramid_levels', [0.03, 0.05, 0.07]),
        'add_dip_pct': s.get('strategy.add_dip_pct', 0.03),
        'take_profit': s.get('strategy.take_profit', []),
        'stop_loss_pct': s.get('strategy.stop_loss_pct', -0.08),
        'trailing_stop_activate': s.get('strategy.trailing_stop.activate_pct', 0.05),
        'trailing_stop_drawdown': s.get('strategy.trailing_stop.drawdown_pct', 0.02),
        't_grid_up': s.get('strategy.grid_t.grid_up', 0.02),
        't_grid_step': s.get('strategy.grid_t.grid_step', 0.015),
        't_grid_max': s.get('strategy.grid_t.grid_max', 3),
        't_buyback_dip': s.get('strategy.grid_t.buyback_dip', 0.01),
        't_sell_ratio': s.get('strategy.grid_t.sell_ratio', 0.20),
        'rsi_buy_max': s.get('strategy.signal.rsi_buy_max', 35),
        'rsi_sell_min': s.get('strategy.signal.rsi_sell_min', 70),
        'volume_confirm': s.get('strategy.signal.volume_confirm', True),
        'volume_ratio_buy': s.get('strategy.signal.volume_ratio_buy', 1.5),
    }

    return CONFIG, TRADE_CONFIG
