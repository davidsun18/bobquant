#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant Optuna 参数优化器 v1.0

功能：
1. 策略参数优化（MACD/RSI/布林带）
2. 目标函数定义（夏普比率、总收益、卡尔马比率等）
3. 剪枝优化（提前终止表现不佳的试验）
4. 可视化结果（参数重要性、优化历史、平行坐标图）

用法：
    from bobquant.optimize.optuna_optimizer import OptunaOptimizer
    
    optimizer = OptunaOptimizer(
        code='000001.SZ',
        start_date='2024-01-01',
        end_date='2024-12-31',
        initial_capital=1000000
    )
    
    # 优化 MACD 策略
    best_params = optimizer.optimize_macd(n_trials=100)
    
    # 查看结果
    optimizer.plot_optimization_history()
    optimizer.plot_parameter_importance()
"""
import optuna
from optuna.visualization import (
    plot_optimization_history,
    plot_param_importances,
    plot_parallel_coordinate,
    plot_slice,
    plot_contour,
    plot_edf,
    plot_terminator_improvement
)
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import json
import os
import warnings
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 非交互式后端

warnings.filterwarnings('ignore')

# 添加项目路径
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)

from backtest.backtrader_engine import (
    MACDStrategy,
    RSIStrategy,
    BollingerStrategy,
    BacktraderEngine
)


class OptunaOptimizer:
    """Optuna 参数优化器"""
    
    def __init__(
        self,
        code: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 1000000,
        data_source: str = 'default'
    ):
        """
        初始化优化器
        
        Args:
            code: 股票代码（如 '000001.SZ'）
            start_date: 开始日期（'YYYY-MM-DD'）
            end_date: 结束日期（'YYYY-MM-DD'）
            initial_capital: 初始资金
            data_source: 数据源
        """
        self.code = code
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.data_source = data_source
        
        # 存储优化结果
        self.study = None
        self.best_params = None
        self.best_value = None
        self.trials_df = None
        
        # 缓存回测引擎
        self.engine = None
        
        # 结果保存目录
        self.results_dir = os.path.join(
            script_dir,
            'results',
            f'{code}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        )
        os.makedirs(self.results_dir, exist_ok=True)
        
        print(f"[优化器] 初始化完成")
        print(f"  - 股票代码：{code}")
        print(f"  - 时间范围：{start_date} ~ {end_date}")
        print(f"  - 初始资金：{initial_capital:,.0f}")
        print(f"  - 结果目录：{self.results_dir}")
    
    def _get_engine(self) -> BacktraderEngine:
        """获取或创建回测引擎实例"""
        if self.engine is None:
            self.engine = BacktraderEngine(
                config={'initial_capital': self.initial_capital}
            )
        return self.engine
    
    def _objective_macd(self, trial: optuna.Trial) -> float:
        """
        MACD 策略目标函数
        
        优化参数：
        - fast_period: 快线周期 (5-20)
        - slow_period: 慢线周期 (20-60)
        - signal_period: 信号线周期 (5-15)
        
        Returns:
            目标函数值（夏普比率）
        """
        # 参数搜索空间
        fast_period = trial.suggest_int('fast_period', 5, 20)
        slow_period = trial.suggest_int('slow_period', 20, 60)
        signal_period = trial.suggest_int('signal_period', 5, 15)
        
        # 确保 fast < slow
        if fast_period >= slow_period:
            fast_period, slow_period = slow_period, fast_period
        
        try:
            engine = self._get_engine()
            results = engine.run_macd(
                code=self.code,
                start_date=self.start_date,
                end_date=self.end_date,
                fast_period=fast_period,
                slow_period=slow_period,
                signal_period=signal_period
            )
            
            # 获取绩效指标
            metrics = results.get('metrics', {})
            
            # 使用夏普比率作为优化目标（允许负值）
            sharpe_ratio = metrics.get('sharpe_ratio', 0)
            
            # 如果夏普比率为 NaN，返回一个很小的值
            if pd.isna(sharpe_ratio):
                return -9999
            
            return sharpe_ratio
            
        except Exception as e:
            print(f"[优化器] 试验失败：{e}")
            return -9999
    
    def _objective_rsi(self, trial: optuna.Trial) -> float:
        """
        RSI 策略目标函数
        
        优化参数：
        - rsi_period: RSI 周期 (7-21)
        - oversold: 超卖阈值 (20-35)
        - overbought: 超买阈值 (65-80)
        
        Returns:
            目标函数值（夏普比率）
        """
        rsi_period = trial.suggest_int('rsi_period', 7, 21)
        oversold = trial.suggest_int('oversold', 20, 35)
        overbought = trial.suggest_int('overbought', 65, 80)
        
        # 确保 oversold < overbought
        if oversold >= overbought:
            oversold, overbought = overbought, oversold
        
        try:
            engine = self._get_engine()
            results = engine.run_rsi(
                code=self.code,
                start_date=self.start_date,
                end_date=self.end_date,
                rsi_period=rsi_period,
                oversold=oversold,
                overbought=overbought
            )
            
            metrics = results.get('metrics', {})
            sharpe_ratio = metrics.get('sharpe_ratio', 0)
            
            if pd.isna(sharpe_ratio):
                return -9999
            
            return sharpe_ratio
            
        except Exception as e:
            print(f"[优化器] 试验失败：{e}")
            return -9999
    
    def _objective_bollinger(self, trial: optuna.Trial) -> float:
        """
        布林带策略目标函数
        
        优化参数：
        - window: 周期 (10-30)
        - num_std: 标准差倍数 (1.5-3.0)
        
        Returns:
            目标函数值（夏普比率）
        """
        window = trial.suggest_int('window', 10, 30)
        num_std = trial.suggest_float('num_std', 1.5, 3.0, step=0.1)
        
        try:
            engine = self._get_engine()
            results = engine.run_bollinger(
                code=self.code,
                start_date=self.start_date,
                end_date=self.end_date,
                window=window,
                num_std=num_std
            )
            
            metrics = results.get('metrics', {})
            sharpe_ratio = metrics.get('sharpe_ratio', 0)
            
            if pd.isna(sharpe_ratio):
                return -9999
            
            return sharpe_ratio
            
        except Exception as e:
            print(f"[优化器] 试验失败：{e}")
            return -9999
    
    def optimize_macd(
        self,
        n_trials: int = 100,
        timeout: Optional[int] = None,
        prune_bad_trials: bool = True,
        study_name: str = 'macd_optimization'
    ) -> Dict:
        """
        优化 MACD 策略参数
        
        Args:
            n_trials: 试验次数
            timeout: 超时时间（秒）
            prune_bad_trials: 是否剪枝表现不佳的试验
            study_name: 研究名称
            
        Returns:
            最优参数字典
        """
        print(f"\n[优化器] 开始优化 MACD 策略")
        print(f"  - 试验次数：{n_trials}")
        print(f"  - 超时时间：{timeout}秒" if timeout else "  - 超时时间：无限制")
        
        # 创建研究
        sampler = optuna.samplers.TPESampler(seed=42)
        pruner = optuna.pruners.MedianPruner(n_startup_trials=10, n_warmup_steps=5) if prune_bad_trials else optuna.pruners.NopPruner()
        
        self.study = optuna.create_study(
            study_name=study_name,
            direction='maximize',
            sampler=sampler,
            pruner=pruner,
            load_if_exists=False
        )
        
        # 运行优化
        self.study.optimize(
            self._objective_macd,
            n_trials=n_trials,
            timeout=timeout,
            show_progress_bar=True,
            gc_after_trial=True
        )
        
        # 保存结果
        self.best_params = self.study.best_params
        self.best_value = self.study.best_value
        self.trials_df = self.study.trials_dataframe()
        
        print(f"\n[优化器] ✅ MACD 优化完成")
        print(f"  - 最优夏普比率：{self.best_value:.4f}")
        print(f"  - 最优参数:")
        for key, value in self.best_params.items():
            print(f"    * {key}: {value}")
        
        # 保存优化结果
        self._save_results('macd')
        
        return self.best_params
    
    def optimize_rsi(
        self,
        n_trials: int = 100,
        timeout: Optional[int] = None,
        prune_bad_trials: bool = True,
        study_name: str = 'rsi_optimization'
    ) -> Dict:
        """
        优化 RSI 策略参数
        
        Args:
            n_trials: 试验次数
            timeout: 超时时间（秒）
            prune_bad_trials: 是否剪枝表现不佳的试验
            study_name: 研究名称
            
        Returns:
            最优参数字典
        """
        print(f"\n[优化器] 开始优化 RSI 策略")
        print(f"  - 试验次数：{n_trials}")
        
        sampler = optuna.samplers.TPESampler(seed=42)
        pruner = optuna.pruners.MedianPruner(n_startup_trials=10, n_warmup_steps=5) if prune_bad_trials else optuna.pruners.NopPruner()
        
        self.study = optuna.create_study(
            study_name=study_name,
            direction='maximize',
            sampler=sampler,
            pruner=pruner,
            load_if_exists=False
        )
        
        self.study.optimize(
            self._objective_rsi,
            n_trials=n_trials,
            timeout=timeout,
            show_progress_bar=True,
            gc_after_trial=True
        )
        
        self.best_params = self.study.best_params
        self.best_value = self.study.best_value
        self.trials_df = self.study.trials_dataframe()
        
        print(f"\n[优化器] ✅ RSI 优化完成")
        print(f"  - 最优夏普比率：{self.best_value:.4f}")
        print(f"  - 最优参数:")
        for key, value in self.best_params.items():
            print(f"    * {key}: {value}")
        
        self._save_results('rsi')
        
        return self.best_params
    
    def optimize_bollinger(
        self,
        n_trials: int = 100,
        timeout: Optional[int] = None,
        prune_bad_trials: bool = True,
        study_name: str = 'bollinger_optimization'
    ) -> Dict:
        """
        优化布林带策略参数
        
        Args:
            n_trials: 试验次数
            timeout: 超时时间（秒）
            prune_bad_trials: 是否剪枝表现不佳的试验
            study_name: 研究名称
            
        Returns:
            最优参数字典
        """
        print(f"\n[优化器] 开始优化布林带策略")
        print(f"  - 试验次数：{n_trials}")
        
        sampler = optuna.samplers.TPESampler(seed=42)
        pruner = optuna.pruners.MedianPruner(n_startup_trials=10, n_warmup_steps=5) if prune_bad_trials else optuna.pruners.NopPruner()
        
        self.study = optuna.create_study(
            study_name=study_name,
            direction='maximize',
            sampler=sampler,
            pruner=pruner,
            load_if_exists=False
        )
        
        self.study.optimize(
            self._objective_bollinger,
            n_trials=n_trials,
            timeout=timeout,
            show_progress_bar=True,
            gc_after_trial=True
        )
        
        self.best_params = self.study.best_params
        self.best_value = self.study.best_value
        self.trials_df = self.study.trials_dataframe()
        
        print(f"\n[优化器] ✅ 布林带优化完成")
        print(f"  - 最优夏普比率：{self.best_value:.4f}")
        print(f"  - 最优参数:")
        for key, value in self.best_params.items():
            print(f"    * {key}: {value}")
        
        self._save_results('bollinger')
        
        return self.best_params
    
    def _save_results(self, strategy_name: str):
        """保存优化结果"""
        if self.study is None:
            return
        
        # 保存研究为 JSON
        study_path = os.path.join(self.results_dir, f'{strategy_name}_study.json')
        study_data = {
            'best_params': self.best_params,
            'best_value': self.best_value,
            'n_trials': len(self.study.trials),
            'direction': self.study.direction.name
        }
        
        with open(study_path, 'w', encoding='utf-8') as f:
            json.dump(study_data, f, indent=2, ensure_ascii=False)
        
        # 保存试验数据为 CSV
        if self.trials_df is not None:
            csv_path = os.path.join(self.results_dir, f'{strategy_name}_trials.csv')
            self.trials_df.to_csv(csv_path, index=False)
        
        print(f"[优化器] 结果已保存到：{self.results_dir}")
    
    def plot_optimization_history(self, save: bool = True):
        """绘制优化历史图"""
        if self.study is None:
            print("[优化器] ⚠️ 没有可用的优化结果")
            return
        
        fig = plot_optimization_history(self.study)
        
        if save:
            # 保存为 HTML（更可靠）
            html_path = os.path.join(self.results_dir, 'optimization_history.html')
            fig.write_html(html_path)
            print(f"[优化器] 📊 优化历史图已保存：{html_path}")
            
            # 尝试保存为 PNG（如果可能）
            try:
                png_path = os.path.join(self.results_dir, 'optimization_history.png')
                fig.write_image(png_path)
                print(f"[优化器] 📊 PNG 图已保存：{png_path}")
            except Exception as e:
                print(f"[优化器] ⚠️ PNG 保存失败：{e}")
        
        return fig
    
    def _save_fig(self, fig, name: str):
        """保存图表为 HTML 和 PNG"""
        # 保存为 HTML（总是成功）
        html_path = os.path.join(self.results_dir, f'{name}.html')
        fig.write_html(html_path)
        print(f"[优化器] 📊 {name}.html 已保存")
        
        # 尝试保存为 PNG
        try:
            png_path = os.path.join(self.results_dir, f'{name}.png')
            fig.write_image(png_path)
            print(f"[优化器] 📊 {name}.png 已保存")
        except Exception as e:
            print(f"[优化器] ⚠️ {name}.png 保存失败：{e}")
    
    def plot_parameter_importance(self, save: bool = True):
        """绘制参数重要性图"""
        if self.study is None:
            print("[优化器] ⚠️ 没有可用的优化结果")
            return
        
        fig = plot_param_importances(self.study)
        
        if save:
            self._save_fig(fig, 'parameter_importance')
        
        return fig
    
    def plot_parallel_coordinate(self, save: bool = True):
        """绘制平行坐标图"""
        if self.study is None:
            print("[优化器] ⚠️ 没有可用的优化结果")
            return
        
        fig = plot_parallel_coordinate(self.study)
        
        if save:
            self._save_fig(fig, 'parallel_coordinate')
        
        return fig
    
    def plot_slice(self, save: bool = True):
        """绘制切片图"""
        if self.study is None:
            print("[优化器] ⚠️ 没有可用的优化结果")
            return
        
        fig = plot_slice(self.study)
        
        if save:
            self._save_fig(fig, 'slice')
        
        return fig
    
    def plot_contour(self, save: bool = True):
        """绘制等高线图"""
        if self.study is None:
            print("[优化器] ⚠️ 没有可用的优化结果")
            return
        
        fig = plot_contour(self.study)
        
        if save:
            self._save_fig(fig, 'contour')
        
        return fig
    
    def plot_edf(self, save: bool = True):
        """绘制累积分布函数图"""
        if self.study is None:
            print("[优化器] ⚠️ 没有可用的优化结果")
            return
        
        fig = plot_edf(self.study)
        
        if save:
            self._save_fig(fig, 'edf')
        
        return fig
    
    def plot_all(self, save: bool = True):
        """绘制所有可视化图表"""
        if self.study is None:
            print("[优化器] ⚠️ 没有可用的优化结果")
            return
        
        print("\n[优化器] 生成所有可视化图表...")
        
        self.plot_optimization_history(save=save)
        self.plot_parameter_importance(save=save)
        self.plot_parallel_coordinate(save=save)
        self.plot_slice(save=save)
        self.plot_contour(save=save)
        self.plot_edf(save=save)
        
        print("[优化器] ✅ 所有图表已生成")
    
    def get_best_trial_info(self) -> Dict:
        """获取最优试验的详细信息"""
        if self.study is None:
            return {}
        
        best_trial = self.study.best_trial
        
        return {
            'number': best_trial.number,
            'value': best_trial.value,
            'params': best_trial.params,
            'datetime_start': best_trial.datetime_start,
            'datetime_complete': best_trial.datetime_complete
        }
    
    def get_trials_summary(self) -> pd.DataFrame:
        """获取试验摘要"""
        if self.trials_df is None:
            return pd.DataFrame()
        
        # 返回前 10 个最佳试验
        top_trials = self.trials_df.nlargest(10, 'value')
        return top_trials[['number', 'value'] + list(self.best_params.keys())]


# ==================== 主函数示例 ====================

if __name__ == '__main__':
    # 示例：优化 MACD 策略
    optimizer = OptunaOptimizer(
        code='000001.SZ',
        start_date='2024-01-01',
        end_date='2024-12-31',
        initial_capital=1000000
    )
    
    # 运行优化（100 次试验）
    best_params = optimizer.optimize_macd(n_trials=100)
    
    # 生成可视化图表
    optimizer.plot_all()
    
    # 查看最优参数
    print("\n最优参数:")
    print(best_params)
