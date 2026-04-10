# -*- coding: utf-8 -*-
"""
FinRL 强化学习模块测试脚本

功能：
- 小规模训练测试
- 验证环境创建
- 测试模型预测
- 生成训练报告
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 直接导入
from finrl_agent import FinRLAgent, RLAlgorithm, create_rl_agent, StockTradingEnv


def generate_test_data(n_days: int = 200, n_stocks: int = 5) -> pd.DataFrame:
    """
    生成模拟股票数据用于测试
    
    Args:
        n_days: 天数
        n_stocks: 股票数量
    
    Returns:
        包含 OHLCV 数据的 DataFrame
    """
    np.random.seed(42)
    
    dates = pd.date_range(start='2024-01-01', periods=n_days, freq='D')
    dates = dates[dates.weekday < 5]  # 只保留工作日
    
    stock_codes = [f"sh.60000{i}" for i in range(n_stocks)]
    
    all_data = []
    
    for i, code in enumerate(stock_codes):
        # 生成随机价格序列（几何布朗运动）
        S0 = 10 + i * 5  # 初始价格
        mu = 0.0005  # 漂移
        sigma = 0.02  # 波动率
        
        returns = np.random.normal(mu, sigma, len(dates))
        prices = S0 * np.exp(np.cumsum(returns))
        
        # 生成 OHLCV
        df = pd.DataFrame({
            'date': dates,
            'code': code,
            'open': prices * (1 + np.random.uniform(-0.01, 0.01, len(dates))),
            'high': prices * (1 + np.random.uniform(0, 0.02, len(dates))),
            'low': prices * (1 - np.random.uniform(0, 0.02, len(dates))),
            'close': prices,
            'volume': np.random.uniform(1e6, 1e7, len(dates)),
        })
        
        all_data.append(df)
    
    # 合并所有股票数据
    full_df = pd.concat(all_data, ignore_index=True)
    
    # 转换为时间序列格式（每行包含所有股票的数据）
    # 这里简化处理，使用单只股票数据进行测试
    test_df = all_data[0].set_index('date')
    
    return test_df, stock_codes[:1]  # 测试使用单只股票


def test_environment():
    """测试交易环境"""
    print("=" * 60)
    print("测试 1: 交易环境创建")
    print("=" * 60)
    
    df, stock_codes = generate_test_data(n_days=100, n_stocks=1)
    
    env = StockTradingEnv(
        df=df,
        stock_codes=stock_codes,
        initial_capital=1_000_000,
        max_stocks=5,
        max_position_pct=0.10,
        window_size=20,
    )
    
    # 测试重置
    obs, info = env.reset()
    print(f"✓ 环境重置成功")
    print(f"  初始观测维度：{obs.shape}")
    print(f"  初始资产：{info['portfolio_value']:.2f}")
    
    # 测试步进
    for i in range(10):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        
        if terminated or truncated:
            break
    
    print(f"✓ 环境步进测试成功")
    print(f"  最终资产：{info['portfolio_value']:.2f}")
    print(f"  交易次数：{info['trades']}")
    print(f"  奖励：{reward:.6f}")
    
    return True


def test_training():
    """测试训练流程"""
    print("\n" + "=" * 60)
    print("测试 2: 模型训练 (小规模)")
    print("=" * 60)
    
    # 生成更多数据用于训练
    df, stock_codes = generate_test_data(n_days=200, n_stocks=1)
    
    # 创建代理
    agent = create_rl_agent(
        algorithm='ppo',
        initial_capital=1_000_000,
        max_stocks=5,
        window_size=30,
        verbose=1,
    )
    
    # 训练模型（小规模测试）
    results = agent.train(
        df=df,
        stock_codes=stock_codes,
        total_timesteps=500,  # 小规模测试
        eval_freq=200,
        n_eval_episodes=3,
        save_path=str(PROJECT_ROOT / 'rl' / 'test_models'),
        learning_rate=3e-4,
        n_steps=128,
        batch_size=32,
        n_epochs=5,
    )
    
    print(f"\n✓ 训练完成!")
    print(f"  算法：{results['algorithm']}")
    print(f"  训练步数：{results['total_timesteps']}")
    print(f"  最终资产：{results['final_portfolio_value']:.2f}")
    print(f"  总交易次数：{results['total_trades']}")
    print(f"  Sharpe 比率：{results['sharpe_ratio']:.4f}")
    
    return agent, results


def test_prediction(agent: FinRLAgent):
    """测试预测功能"""
    print("\n" + "=" * 60)
    print("测试 3: 模型预测")
    print("=" * 60)
    
    # 生成测试数据
    df, stock_codes = generate_test_data(n_days=100, n_stocks=1)
    
    # 预测
    actions, details = agent.predict(
        df=df,
        stock_codes=stock_codes,
        n_steps=50,
    )
    
    print(f"✓ 预测完成!")
    print(f"  预测步数：{len(actions)}")
    print(f"  最终资产：{details['final_value']:.2f}")
    print(f"  总交易次数：{details['total_trades']}")
    print(f"  Sharpe 比率：{details['sharpe_ratio']:.4f}")
    
    # 显示前 10 个动作
    action_names = {0: '持有', 1: '买入', 2: '卖出'}
    print(f"\n  前 10 个动作：")
    for i, action in enumerate(actions[:10]):
        print(f"    Step {i}: {action_names.get(action, str(action))}")
    
    return details


def test_evaluation(agent: FinRLAgent):
    """测试策略评估"""
    print("\n" + "=" * 60)
    print("测试 4: 策略评估")
    print("=" * 60)
    
    # 生成测试数据
    df, stock_codes = generate_test_data(n_days=150, n_stocks=1)
    
    # 评估
    metrics = agent.evaluate_strategy(
        df=df,
        stock_codes=stock_codes,
    )
    
    print(f"✓ 评估完成!")
    print(f"  总收益率：{metrics['total_return']*100:.2f}%")
    print(f"  Sharpe 比率：{metrics['sharpe_ratio']:.4f}")
    print(f"  最大回撤：{metrics['max_drawdown']*100:.2f}%")
    print(f"  年化波动率：{metrics['volatility']*100:.2f}%")
    print(f"  总交易次数：{metrics['total_trades']}")
    print(f"  最终资产：{metrics['final_value']:.2f}")
    
    return metrics


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("BobQuant FinRL 强化学习模块测试")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # 测试 1: 环境
        env_ok = test_environment()
        
        if not env_ok:
            print("\n✗ 环境测试失败，终止测试")
            return False
        
        # 测试 2: 训练
        agent, train_results = test_training()
        
        # 测试 3: 预测
        pred_details = test_prediction(agent)
        
        # 测试 4: 评估
        eval_metrics = test_evaluation(agent)
        
        # 总结
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        print("✓ 所有测试通过!")
        print(f"\n创建的文件:")
        print(f"  - bobquant/rl/finrl_agent.py (强化学习代理)")
        print(f"  - bobquant/rl/test_models/ (训练模型)")
        print(f"  - bobquant/config/settings.yaml (已添加 RL 配置)")
        
        print(f"\n训练结果摘要:")
        print(f"  - 算法：{train_results['algorithm']}")
        print(f"  - 训练步数：{train_results['total_timesteps']}")
        print(f"  - 最终资产：{train_results['final_portfolio_value']:.2f} (初始：1,000,000)")
        print(f"  - Sharpe 比率：{train_results['sharpe_ratio']:.4f}")
        print(f"  - 总交易次数：{train_results['total_trades']}")
        
        print(f"\n与 ML 模块集成方案:")
        print(f"  1. 在 bobquant/ml/predictor.py 中添加 RL 预测器类")
        print(f"  2. 在 config/settings.yaml 中配置 rl.enabled=true 启用")
        print(f"  3. 在 main.py 中添加 RL 策略信号生成")
        print(f"  4. 可与现有 ML 模型集成，形成混合策略")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
