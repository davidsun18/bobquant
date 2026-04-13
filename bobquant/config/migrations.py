# -*- coding: utf-8 -*-
"""
BobQuant 配置迁移系统

提供配置版本迁移功能，支持：
- 旧版本配置自动升级到新版本
- 自定义迁移步骤
- 迁移回滚
- 迁移验证
"""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Tuple
from datetime import datetime
from pydantic import BaseModel, Field


class MigrationError(Exception):
    """迁移错误"""
    def __init__(self, message: str, source_version: str = "", target_version: str = ""):
        self.message = message
        self.source_version = source_version
        self.target_version = target_version
        super().__init__(self.format_message())
    
    def format_message(self) -> str:
        msg = f"迁移失败：{self.message}"
        if self.source_version and self.target_version:
            msg = f"{msg} (从 {self.source_version} 到 {self.target_version})"
        return msg


class MigrationStep(BaseModel):
    """单个迁移步骤"""
    source_version: str = Field(..., description="源版本号")
    target_version: str = Field(..., description="目标版本号")
    description: str = Field(default="", description="迁移描述")
    migrate_func: Optional[Callable[[Dict], Dict]] = Field(default=None, description="迁移函数", exclude=True)
    rollback_func: Optional[Callable[[Dict], Dict]] = Field(default=None, description="回滚函数", exclude=True)
    
    def migrate(self, config: Dict) -> Dict:
        """执行迁移"""
        if self.migrate_func:
            return self.migrate_func(config)
        return config
    
    def rollback(self, config: Dict) -> Dict:
        """执行回滚"""
        if self.rollback_func:
            return self.rollback_func(config)
        return config


class MigrationRecord(BaseModel):
    """迁移记录"""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    source_version: str = Field(..., description="源版本号")
    target_version: str = Field(..., description="目标版本号")
    success: bool = Field(..., description="是否成功")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    backup_path: Optional[str] = Field(default=None, description="备份文件路径")


class ConfigMigrator:
    """
    配置迁移器
    
    功能：
    - 检测配置版本
    - 自动执行迁移步骤
    - 支持回滚
    - 备份原配置
    """
    
    # 当前配置版本
    CURRENT_VERSION = "3.0"
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        self.migration_steps: Dict[Tuple[str, str], MigrationStep] = {}
        self.migration_history: List[MigrationRecord] = []
        self._register_builtin_migrations()
    
    def _register_builtin_migrations(self):
        """注册内置迁移步骤"""
        
        # v2.2 -> v3.0: 重构配置结构
        self.register_step(MigrationStep(
            source_version="2.2",
            target_version="3.0",
            description="重构配置结构，支持 5 层继承",
            migrate_func=self._migrate_v22_to_v30,
            rollback_func=self._rollback_v30_to_v22
        ))
        
        # v2.4 -> v3.0: 激进配置迁移
        self.register_step(MigrationStep(
            source_version="2.4",
            target_version="3.0",
            description="从激进配置迁移到 v3.0",
            migrate_func=self._migrate_v24_to_v30,
            rollback_func=self._rollback_v30_to_v24
        ))
    
    def register_step(self, step: MigrationStep):
        """注册迁移步骤"""
        key = (step.source_version, step.target_version)
        self.migration_steps[key] = step
    
    def detect_version(self, config: Dict) -> str:
        """
        检测配置版本
        
        优先级：
        1. system.version 字段
        2. 文件名中的版本号
        3. 默认为 "1.0"
        """
        # 检查 system.version
        if "system" in config and isinstance(config["system"], dict):
            version = config["system"].get("version")
            if version:
                return str(version)
        
        # 检查顶层 version
        version = config.get("version")
        if version:
            return str(version)
        
        # 检查配置文件名
        if self.config_path:
            name = self.config_path.stem
            # 匹配 sim_config_v2_2.yaml -> 2.2
            import re
            match = re.search(r'v(\d+\.?\d*)', name)
            if match:
                return match.group(1)
        
        return "1.0"
    
    def needs_migration(self, config: Dict) -> bool:
        """检查是否需要迁移"""
        current = self.detect_version(config)
        return current != self.CURRENT_VERSION
    
    def get_migration_plan(self, from_version: str) -> List[MigrationStep]:
        """
        获取迁移计划
        
        使用 BFS 找到从 from_version 到 CURRENT_VERSION 的最短路径
        """
        if from_version == self.CURRENT_VERSION:
            return []
        
        # 构建版本图
        from collections import defaultdict, deque
        
        graph = defaultdict(list)
        for (src, tgt), step in self.migration_steps.items():
            graph[src].append((tgt, step))
        
        # BFS 找最短路径
        queue = deque([(from_version, [])])
        visited = {from_version}
        
        while queue:
            current, path = queue.popleft()
            
            for next_version, step in graph[current]:
                if next_version == self.CURRENT_VERSION:
                    return path + [step]
                
                if next_version not in visited:
                    visited.add(next_version)
                    queue.append((next_version, path + [step]))
        
        # 找不到路径
        raise MigrationError(
            f"无法找到从 {from_version} 到 {self.CURRENT_VERSION} 的迁移路径",
            source_version=from_version,
            target_version=self.CURRENT_VERSION
        )
    
    def migrate(self, 
                config: Optional[Dict] = None,
                config_path: Optional[Path] = None,
                backup: bool = True) -> Tuple[Dict, List[MigrationRecord]]:
        """
        执行迁移
        
        Args:
            config: 配置字典（与 config_path 二选一）
            config_path: 配置文件路径
            backup: 是否备份原配置
        
        Returns:
            (迁移后的配置，迁移记录列表)
        """
        import json5
        
        # 加载配置
        if config is None:
            path = config_path or self.config_path
            if not path:
                raise ValueError("必须提供 config 或 config_path")
            
            content = path.read_text(encoding='utf-8')
            config = json5.loads(content)
        
        # 检测版本
        from_version = self.detect_version(config)
        
        if from_version == self.CURRENT_VERSION:
            return config, []
        
        # 获取迁移计划
        plan = self.get_migration_plan(from_version)
        
        # 备份原配置
        backup_path = None
        if backup and self.config_path:
            backup_path = self._backup_config(self.config_path)
        
        # 执行迁移
        records = []
        current_config = config
        
        for i, step in enumerate(plan):
            record = MigrationRecord(
                source_version=step.source_version,
                target_version=step.target_version,
                success=False,
                backup_path=backup_path
            )
            
            try:
                current_config = step.migrate(current_config)
                record.success = True
                
                # 更新版本号
                if "system" not in current_config:
                    current_config["system"] = {}
                current_config["system"]["version"] = step.target_version
                
            except Exception as e:
                record.error_message = str(e)
                raise MigrationError(
                    f"迁移步骤 {i+1}/{len(plan)} 失败：{e}",
                    source_version=step.source_version,
                    target_version=step.target_version
                )
            finally:
                records.append(record)
        
        self.migration_history.extend(records)
        
        return current_config, records
    
    def migrate_file(self, 
                     source_path: Path,
                     target_path: Optional[Path] = None,
                     backup: bool = True) -> Tuple[Path, List[MigrationRecord]]:
        """
        迁移配置文件
        
        Args:
            source_path: 源配置文件路径
            target_path: 目标路径（为空则覆盖原文件）
            backup: 是否备份
        
        Returns:
            (目标文件路径，迁移记录)
        """
        import json5
        
        # 加载配置
        content = source_path.read_text(encoding='utf-8')
        config = json5.loads(content)
        
        # 执行迁移
        migrated_config, records = self.migrate(config=config, backup=backup)
        
        # 保存到新文件
        target = target_path or source_path
        target.write_text(json.dumps(migrated_config, indent=2, ensure_ascii=False), encoding='utf-8')
        
        return target, records
    
    def rollback(self, 
                 config: Dict,
                 to_version: str) -> Tuple[Dict, List[MigrationRecord]]:
        """
        回滚配置到指定版本
        
        Args:
            config: 当前配置
            to_version: 目标版本
        
        Returns:
            (回滚后的配置，迁移记录)
        """
        from_version = self.detect_version(config)
        
        if from_version == to_version:
            return config, []
        
        # 获取回滚路径（反向迁移）
        plan = self.get_migration_plan(to_version)
        plan.reverse()
        
        records = []
        current_config = config
        
        for i, step in enumerate(plan):
            record = MigrationRecord(
                source_version=step.target_version,
                target_version=step.source_version,
                success=False
            )
            
            try:
                current_config = step.rollback(current_config)
                record.success = True
                current_config["system"]["version"] = step.source_version
                
            except Exception as e:
                record.error_message = str(e)
                raise MigrationError(
                    f"回滚步骤 {i+1}/{len(plan)} 失败：{e}",
                    source_version=step.target_version,
                    target_version=step.source_version
                )
            finally:
                records.append(record)
        
        return current_config, records
    
    def _backup_config(self, config_path: Path) -> str:
        """备份配置文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{config_path.stem}.backup.{timestamp}{config_path.suffix}"
        backup_path = config_path.parent / backup_name
        shutil.copy2(config_path, backup_path)
        return str(backup_path)
    
    # ==================== 迁移函数实现 ====================
    
    def _migrate_v22_to_v30(self, config: Dict) -> Dict:
        """
        v2.2 -> v3.0 迁移
        
        变更：
        1. 添加 system 层
        2. 重组 account 配置
        3. 添加 5 层继承支持
        4. 支持 SecretRef
        """
        migrated = config.copy()
        
        # 确保 system 层存在
        if "system" not in migrated:
            migrated["system"] = {}
        
        if "version" in migrated:
            migrated["system"]["version"] = migrated.pop("version")
        else:
            migrated["system"]["version"] = "3.0"
        
        if "name" in migrated:
            migrated["system"]["name"] = migrated.pop("name")
        else:
            migrated["system"]["name"] = "BobQuant"
        
        if "mode" in migrated:
            migrated["system"]["mode"] = migrated.pop("mode")
        else:
            migrated["system"]["mode"] = "simulation"
        
        # 重组 account 配置
        if "account" in migrated:
            acc = migrated["account"]
            # 移动仓位相关配置到 position
            if "max_position_pct" in acc or "max_stocks" in acc:
                if "position" not in migrated:
                    migrated["position"] = {}
                
                if "max_position_pct" in acc:
                    migrated["position"]["max_position_pct"] = acc.pop("max_position_pct")
                if "max_stocks" in acc:
                    migrated["position"]["max_stocks"] = acc.pop("max_stocks")
        
        # 重组 risk_control
        if "strategy" in migrated:
            strat = migrated["strategy"]
            risk_control = {}
            
            # 提取止损配置
            if "stop_loss_pct" in strat:
                risk_control["stop_loss"] = {
                    "enabled": True,
                    "pct": strat.pop("stop_loss_pct")
                }
            
            # 提取跟踪止损
            if "trailing_stop_activate" in strat or "trailing_stop_drawdown" in strat:
                risk_control["trailing_stop"] = {}
                if "trailing_stop_activate" in strat:
                    risk_control["trailing_stop"]["activation_pct"] = strat.pop("trailing_stop_activate")
                if "trailing_stop_drawdown" in strat:
                    risk_control["trailing_stop"]["drawdown_pct"] = strat.pop("trailing_stop_drawdown")
            
            # 提取止盈配置
            if "take_profit" in strat:
                risk_control["take_profit"] = strat.pop("take_profit")
            
            if risk_control:
                migrated["risk_control"] = risk_control
        
        # 添加 5 层继承字段
        migrated.setdefault("global_defaults", {})
        migrated.setdefault("strategy_configs", {})
        migrated.setdefault("channel_configs", {})
        migrated.setdefault("account_configs", {})
        migrated.setdefault("group_configs", {})
        
        return migrated
    
    def _rollback_v30_to_v22(self, config: Dict) -> Dict:
        """v3.0 -> v2.2 回滚"""
        migrated = config.copy()
        
        # 恢复 version 到顶层
        if "system" in migrated:
            sys = migrated["system"]
            if "version" in sys:
                migrated["version"] = sys.pop("version")
            if "name" in sys:
                migrated["name"] = sys.pop("name")
            if "mode" in sys:
                migrated["mode"] = sys.pop("mode")
            if not sys:
                migrated.pop("system")
        
        # 恢复 account 配置
        if "position" in migrated:
            pos = migrated["position"]
            if "account" not in migrated:
                migrated["account"] = {}
            
            if "max_position_pct" in pos:
                migrated["account"]["max_position_pct"] = pos.pop("max_position_pct")
            if "max_stocks" in pos:
                migrated["account"]["max_stocks"] = pos.pop("max_stocks")
        
        # 恢复 strategy 配置
        if "risk_control" in migrated:
            rc = migrated["risk_control"]
            if "strategy" not in migrated:
                migrated["strategy"] = {}
            
            strat = migrated["strategy"]
            
            if "stop_loss" in rc and "pct" in rc["stop_loss"]:
                strat["stop_loss_pct"] = rc["stop_loss"]["pct"]
            
            if "trailing_stop" in rc:
                ts = rc["trailing_stop"]
                if "activation_pct" in ts:
                    strat["trailing_stop_activate"] = ts["activation_pct"]
                if "drawdown_pct" in ts:
                    strat["trailing_stop_drawdown"] = ts["drawdown_pct"]
            
            if "take_profit" in rc:
                strat["take_profit"] = rc["take_profit"]
        
        # 移除 5 层继承字段
        for key in ["global_defaults", "strategy_configs", "channel_configs", 
                    "account_configs", "group_configs"]:
            migrated.pop(key, None)
        
        return migrated
    
    def _migrate_v24_to_v30(self, config: Dict) -> Dict:
        """v2.4 -> v3.0 迁移（激进配置）"""
        # v2.4 配置基本兼容 v3.0，只需添加 5 层继承支持
        migrated = self._migrate_v22_to_v30(config)
        
        # 标记为激进策略
        if "strategy_configs" not in migrated:
            migrated["strategy_configs"] = {}
        
        migrated["strategy_configs"]["aggressive"] = {
            "strategy_name": "aggressive",
            "position": {"max_position_pct": 0.15},
            "risk_control": {"stop_loss": {"pct": -0.10}}
        }
        
        migrated["active_strategy"] = "aggressive"
        
        return migrated
    
    def _rollback_v30_to_v24(self, config: Dict) -> Dict:
        """v3.0 -> v2.4 回滚"""
        migrated = self._rollback_v30_to_v22(config)
        
        # 恢复 v2.4 特定配置
        if "active_strategy" in migrated:
            migrated.pop("active_strategy")
        
        return migrated
    
    def get_history(self) -> List[MigrationRecord]:
        """获取迁移历史"""
        return self.migration_history
    
    def get_history_report(self) -> str:
        """获取迁移历史报告"""
        if not self.migration_history:
            return "暂无迁移记录"
        
        report = ["迁移历史记录："]
        for record in self.migration_history:
            status = "✓" if record.success else "✗"
            report.append(
                f"  {status} {record.timestamp}: {record.source_version} → "
                f"{record.target_version}" +
                (f" (错误：{record.error_message})" if record.error_message else "")
            )
        
        return "\n".join(report)


# ==================== 便捷函数 ====================

def migrate_config(config_path: Path, 
                   backup: bool = True,
                   target_path: Optional[Path] = None) -> Tuple[Path, List[MigrationRecord]]:
    """
    便捷函数：迁移配置文件
    
    Args:
        config_path: 配置文件路径
        backup: 是否备份
        target_path: 目标路径
    
    Returns:
        (目标文件路径，迁移记录)
    """
    migrator = ConfigMigrator(config_path)
    return migrator.migrate_file(config_path, target_path, backup)


def check_config_version(config_path: Path) -> str:
    """
    便捷函数：检查配置文件版本
    
    Returns:
        版本号
    """
    import json5
    migrator = ConfigMigrator(config_path)
    content = config_path.read_text(encoding='utf-8')
    config = json5.loads(content)
    return migrator.detect_version(config)


def needs_migration(config_path: Path) -> bool:
    """
    便捷函数：检查是否需要迁移
    
    Returns:
        是否需要迁移
    """
    import json5
    migrator = ConfigMigrator(config_path)
    content = config_path.read_text(encoding='utf-8')
    config = json5.loads(content)
    return migrator.needs_migration(config)
