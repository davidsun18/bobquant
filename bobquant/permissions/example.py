# -*- coding: utf-8 -*-
"""
BobQuant 权限系统使用示例
演示完整的权限控制流程
"""

import logging
from .engine import PermissionEngine, PermissionMode, PermissionRequest
from .rules import RuleMatcher, Rule, RuleAction, DefaultRules, create_rule
from .classifier import TradeClassifier, rule_profit_take_auto_approve, rule_loss_cut_auto_approve

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def example_basic_usage():
    """基础使用示例"""
    print("=" * 60)
    print("示例 1: 基础权限检查")
    print("=" * 60)
    
    # 1. 创建权限引擎 (默认模式：需要询问)
    engine = PermissionEngine(mode=PermissionMode.DEFAULT)
    
    # 2. 创建权限请求
    request = PermissionRequest(
        action="trade",
        symbol="sh.600000",
        side="buy",
        quantity=100,
        price=10.5,
        order_type="limit",
        strategy="grid",
    )
    
    # 3. 检查权限
    response = engine.check_permission(request)
    
    print(f"请求：{request.symbol} {request.side} {request.quantity}股 @ {request.price}")
    print(f"授权：{'✓ 允许' if response.granted else '✗ 拒绝'}")
    print(f"模式：{response.mode.name}")
    print(f"原因：{response.reason}")
    print(f"需要确认：{response.requires_confirmation}")
    print()


def example_rule_matching():
    """规则匹配示例"""
    print("=" * 60)
    print("示例 2: 规则匹配")
    print("=" * 60)
    
    # 1. 创建规则匹配器
    matcher = RuleMatcher()
    
    # 2. 添加默认规则
    matcher.add_rules(DefaultRules.get_default_rules())
    
    # 3. 添加自定义规则
    matcher.add_rule(create_rule(
        pattern="Trade(000001.*)",
        action="allow",
        priority=100,
        description="允许交易平安银行"
    ))
    
    # 4. 测试匹配
    test_symbols = ["000001", "600000", "300001", "688001"]
    
    for symbol in test_symbols:
        result = matcher.match(symbol, "trade")
        print(f"{symbol}: {result['action']} (规则：{result['rule']})")
    
    print()


def example_ai_classifier():
    """AI 分类器示例"""
    print("=" * 60)
    print("示例 3: AI 分类器")
    print("=" * 60)
    
    # 1. 创建分类器
    classifier = TradeClassifier(
        auto_approve_threshold=10000,  # 1 万元以下自动批准
        auto_deny_threshold=100000,    # 10 万元以上自动拒绝
    )
    
    # 2. 添加自定义规则
    classifier.add_custom_rule(rule_profit_take_auto_approve)
    classifier.add_custom_rule(rule_loss_cut_auto_approve)
    
    # 3. 测试不同场景
    test_cases = [
        {
            'symbol': 'sh.600000',
            'side': 'buy',
            'quantity': 100,
            'price': 10.0,
            'strategy': 'grid',
            'board_type': '主板',
        },
        {
            'symbol': 'sz.300001',
            'side': 'buy',
            'quantity': 1000,
            'price': 50.0,
            'strategy': 'momentum',
            'board_type': '创业板',
            'price_change_pct': 9.5,
        },
        {
            'symbol': 'sh.600000',
            'side': 'sell',
            'quantity': 100,
            'price': 12.0,
            'strategy': 'grid',
            'board_type': '主板',
            'profit_rate': 25.0,  # 盈利 25%
        },
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        result = classifier.classify(**case)
        print(f"  决策：{'✓ 允许' if result['granted'] else '✗ 拒绝'}")
        print(f"  原因：{result['reason']}")
        print(f"  风险等级：{result['risk_level']}")
    
    print()


def example_grace_period():
    """优雅期示例"""
    print("=" * 60)
    print("示例 4: 优雅期 (防误触)")
    print("=" * 60)
    
    import time
    from .engine import PermissionEngine, PermissionMode, PermissionRequest
    
    # 创建引擎 (200ms 优雅期)
    engine = PermissionEngine(
        mode=PermissionMode.ACCEPT_EDITS,
        grace_period_ms=200.0
    )
    
    request = PermissionRequest(
        action="trade",
        symbol="sh.600000",
        side="buy",
        quantity=100,
        price=10.0,
    )
    
    # 快速连续请求
    for i in range(3):
        response = engine.check_permission(request)
        print(f"请求 {i+1}: 优雅期剩余={response.grace_period_remaining*1000:.1f}ms")
        time.sleep(0.1)  # 100ms 间隔
    
    print()


def example_denial_tracking():
    """拒绝追踪示例"""
    print("=" * 60)
    print("示例 5: 拒绝次数追踪和降级")
    print("=" * 60)
    
    from .engine import PermissionEngine, PermissionMode, PermissionRequest
    
    # 创建引擎 (3 次拒绝后降级)
    engine = PermissionEngine(
        mode=PermissionMode.AUTO,
        denial_threshold=3,
    )
    
    request = PermissionRequest(
        action="trade",
        symbol="sh.600000",
        side="buy",
        quantity=100,
        price=10.0,
    )
    
    # 模拟多次拒绝
    for i in range(5):
        response = engine.check_permission(request)
        print(f"请求 {i+1}:")
        print(f"  拒绝次数：{response.denial_count}")
        print(f"  已降级：{response.degraded}")
        print()


def example_full_workflow():
    """完整工作流示例"""
    print("=" * 60)
    print("示例 6: 完整权限工作流")
    print("=" * 60)
    
    # 1. 初始化组件
    engine = PermissionEngine(
        mode=PermissionMode.AUTO,
        grace_period_ms=200.0,
        denial_threshold=3,
    )
    
    matcher = RuleMatcher()
    matcher.add_rules(DefaultRules.get_default_rules())
    
    classifier = TradeClassifier(auto_approve_threshold=10000)
    classifier.add_custom_rule(rule_profit_take_auto_approve)
    
    # 将分类器集成到引擎
    def classifier_callback(request):
        return classifier.classify(
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            price=request.price or 0,
            strategy=request.strategy,
        )
    
    engine.classifier_callback = classifier_callback
    
    # 2. 模拟交易请求
    requests = [
        PermissionRequest(
            action="trade",
            symbol="000001",
            side="buy",
            quantity=100,
            price=10.0,
            strategy="grid",
        ),
        PermissionRequest(
            action="trade",
            symbol="300001",
            side="buy",
            quantity=500,
            price=50.0,
            strategy="momentum",
            risk_level="high",
        ),
        PermissionRequest(
            action="trade",
            symbol="sh.600000",
            side="sell",
            quantity=100,
            price=12.0,
            strategy="grid",
            metadata={'profit_rate': 25.0},
        ),
    ]
    
    # 3. 处理请求
    for i, request in enumerate(requests, 1):
        print(f"\n请求 {i}: {request.symbol} {request.side}")
        
        # 检查权限
        response = engine.check_permission(request, rule_matcher=matcher)
        
        print(f"  授权：{'✓' if response.granted else '✗'}")
        print(f"  原因：{response.reason}")
        print(f"  需要确认：{response.requires_confirmation}")
        
        # 如果需要确认，模拟用户确认
        if response.requires_confirmation:
            # 实际应用中这里会等待用户输入
            confirmed = True  # 模拟用户确认
            engine.confirm_permission(request, confirmed)
            print(f"  用户确认：{'✓' if confirmed else '✗'}")
    
    print()
    
    # 4. 显示引擎状态
    status = engine.get_status()
    print("引擎状态:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print()


def example_permission_modes():
    """权限模式演示"""
    print("=" * 60)
    print("示例 7: 权限模式对比")
    print("=" * 60)
    
    from .engine import PermissionEngine, PermissionMode, PermissionRequest
    
    request = PermissionRequest(
        action="trade",
        symbol="sh.600000",
        side="buy",
        quantity=100,
        price=10.0,
    )
    
    modes = [
        PermissionMode.ACCEPT_EDITS,
        PermissionMode.BYPASS_PERMISSIONS,
        PermissionMode.DEFAULT,
        PermissionMode.PLAN,
        PermissionMode.AUTO,
    ]
    
    for mode in modes:
        engine = PermissionEngine(mode=mode)
        response = engine.check_permission(request)
        
        status = "✓" if response.granted else ("?" if response.requires_confirmation else "✗")
        print(f"{mode.name:25} {status} - {response.reason}")
    
    print()


def main():
    """运行所有示例"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "BobQuant 权限系统示例" + " " * 25 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    example_basic_usage()
    example_rule_matching()
    example_ai_classifier()
    example_grace_period()
    example_denial_tracking()
    example_full_workflow()
    example_permission_modes()
    
    print("=" * 60)
    print("所有示例完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
