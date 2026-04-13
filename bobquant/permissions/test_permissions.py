# -*- coding: utf-8 -*-
"""
BobQuant 权限系统单元测试
"""

import unittest
import time
from .engine import PermissionEngine, PermissionMode, PermissionRequest, GracePeriodManager, DenialTracker
from .rules import RuleMatcher, Rule, RuleAction, RuleType, create_rule, DefaultRules
from .classifier import TradeClassifier, RiskLevel, rule_profit_take_auto_approve


class TestPermissionEngine(unittest.TestCase):
    """权限引擎测试"""
    
    def test_accept_edits_mode(self):
        """测试允许交易模式"""
        engine = PermissionEngine(mode=PermissionMode.ACCEPT_EDITS)
        request = PermissionRequest(
            action="trade", symbol="sh.600000", side="buy", quantity=100, price=10.0
        )
        response = engine.check_permission(request)
        self.assertTrue(response.granted)
        self.assertEqual(response.mode, PermissionMode.ACCEPT_EDITS)
    
    def test_bypass_permissions_mode(self):
        """测试跳过风控模式"""
        engine = PermissionEngine(mode=PermissionMode.BYPASS_PERMISSIONS)
        request = PermissionRequest(
            action="trade", symbol="sh.600000", side="buy", quantity=100, price=10.0
        )
        response = engine.check_permission(request)
        self.assertTrue(response.granted)
    
    def test_plan_mode(self):
        """测试计划模式"""
        engine = PermissionEngine(mode=PermissionMode.PLAN)
        request = PermissionRequest(
            action="trade", symbol="sh.600000", side="buy", quantity=100, price=10.0
        )
        response = engine.check_permission(request)
        self.assertFalse(response.granted)
        self.assertFalse(response.requires_confirmation)
    
    def test_default_mode(self):
        """测试默认模式"""
        engine = PermissionEngine(mode=PermissionMode.DEFAULT)
        request = PermissionRequest(
            action="trade", symbol="sh.600000", side="buy", quantity=100, price=10.0
        )
        response = engine.check_permission(request)
        self.assertFalse(response.granted)
        self.assertTrue(response.requires_confirmation)
    
    def test_confirm_permission(self):
        """测试用户确认"""
        engine = PermissionEngine(mode=PermissionMode.DEFAULT)
        request = PermissionRequest(
            action="trade", symbol="sh.600000", side="buy", quantity=100, price=10.0
        )
        
        # 确认后拒绝计数应重置
        engine.confirm_permission(request, confirmed=True)
        key = f"{request.action}:{request.symbol}"
        self.assertEqual(engine.denial_tracker.get_denial_count(key), 0)


class TestGracePeriod(unittest.TestCase):
    """优雅期测试"""
    
    def test_grace_period_detection(self):
        """测试优雅期检测"""
        manager = GracePeriodManager(grace_period_ms=200.0)
        request = PermissionRequest(
            action="trade", symbol="sh.600000", side="buy", quantity=100, price=10.0
        )
        
        # 第一次请求不在优雅期
        in_grace, remaining = manager.check_grace_period(request)
        self.assertFalse(in_grace)
        
        # 立即第二次请求应在优雅期
        in_grace, remaining = manager.check_grace_period(request)
        self.assertTrue(in_grace)
        self.assertGreater(remaining, 0)
        
        # 等待 250ms 后应不在优雅期
        time.sleep(0.25)
        in_grace, remaining = manager.check_grace_period(request)
        self.assertFalse(in_grace)


class TestDenialTracker(unittest.TestCase):
    """拒绝追踪测试"""
    
    def test_denial_counting(self):
        """测试拒绝计数"""
        tracker = DenialTracker(threshold=3)
        request = PermissionRequest(
            action="trade", symbol="sh.600000", side="buy", quantity=100, price=10.0
        )
        
        key = "trade:sh.600000"
        
        # 初始为 0
        self.assertEqual(tracker.get_denial_count(key), 0)
        self.assertFalse(tracker.is_degraded(key))
        
        # 记录 2 次拒绝
        tracker.record_denial(key, request, "test")
        tracker.record_denial(key, request, "test")
        self.assertEqual(tracker.get_denial_count(key), 2)
        self.assertFalse(tracker.is_degraded(key))
        
        # 记录第 3 次拒绝，应触发降级
        tracker.record_denial(key, request, "test")
        self.assertEqual(tracker.get_denial_count(key), 3)
        self.assertTrue(tracker.is_degraded(key))
    
    def test_denial_reset(self):
        """测试拒绝重置"""
        tracker = DenialTracker(threshold=3)
        request = PermissionRequest(
            action="trade", symbol="sh.600000", side="buy", quantity=100, price=10.0
        )
        
        key = "trade:sh.600000"
        tracker.record_denial(key, request, "test")
        tracker.record_denial(key, request, "test")
        
        tracker.reset(key)
        self.assertEqual(tracker.get_denial_count(key), 0)


class TestRuleMatcher(unittest.TestCase):
    """规则匹配测试"""
    
    def test_wildcard_matching(self):
        """测试通配符匹配"""
        matcher = RuleMatcher()
        
        # 添加规则 (使用 * 而不是 .* 因为 .是字面量)
        matcher.add_rule(create_rule(
            pattern="Trade(000001)",
            action="allow",
            priority=100
        ))
        matcher.add_rule(create_rule(
            pattern="Trade(600*)",
            action="allow",
            priority=90
        ))
        matcher.add_rule(create_rule(
            pattern="Trade(300*)",
            action="ask",
            priority=80
        ))
        
        # 测试匹配
        result = matcher.match("000001", "trade")
        self.assertEqual(result['action'], 'allow')
        
        result = matcher.match("600000", "trade")
        self.assertEqual(result['action'], 'allow')
        
        result = matcher.match("300001", "trade")
        self.assertEqual(result['action'], 'ask')
    
    def test_risk_rule(self):
        """测试风控规则"""
        matcher = RuleMatcher()
        matcher.add_rule(create_rule(
            pattern="Risk(*)",
            action="allow",
            priority=100
        ))
        
        result = matcher.match("any_risk_check", "risk")
        self.assertEqual(result['action'], 'allow')
    
    def test_default_rules(self):
        """测试默认规则集"""
        matcher = RuleMatcher()
        matcher.add_rules(DefaultRules.get_default_rules())
        
        # 平安银行应允许
        result = matcher.match("000001", "trade")
        self.assertEqual(result['action'], 'allow')
        
        # 沪市主板应允许
        result = matcher.match("600000", "trade")
        self.assertEqual(result['action'], 'allow')


class TestTradeClassifier(unittest.TestCase):
    """AI 分类器测试"""
    
    def test_low_risk_trade(self):
        """测试低风险交易"""
        classifier = TradeClassifier(auto_approve_threshold=10000)
        
        result = classifier.classify(
            symbol="sh.600000",
            side="buy",
            quantity=100,
            price=10.0,
            strategy="grid",
            board_type="主板",
        )
        
        # 小额网格交易应该被批准 (可能是 LOW 或 NORMAL，但应该 granted)
        self.assertTrue(result['granted'])
        # 风险等级应该是 LOW 或 NORMAL
        self.assertIn(result['risk_level'], ['LOW', 'NORMAL'])
    
    def test_high_risk_trade(self):
        """测试高风险交易"""
        classifier = TradeClassifier(auto_approve_threshold=10000)
        
        result = classifier.classify(
            symbol="sz.300001",
            side="buy",
            quantity=1000,
            price=50.0,
            strategy="momentum",
            board_type="创业板",
            price_change_pct=9.5,
        )
        
        self.assertFalse(result['granted'])
        self.assertIn(result['risk_level'], ['HIGH', 'CRITICAL'])
    
    def test_profit_take_rule(self):
        """测试止盈规则"""
        classifier = TradeClassifier()
        classifier.add_custom_rule(rule_profit_take_auto_approve)
        
        result = classifier.classify(
            symbol="sh.600000",
            side="sell",
            quantity=100,
            price=12.0,
            strategy="grid",
            board_type="主板",
            profit_rate=25.0,
        )
        
        self.assertTrue(result['granted'])
        self.assertIn('止盈', result['reason'])
    
    def test_board_risk_factor(self):
        """测试板块风险系数"""
        classifier = TradeClassifier(auto_approve_threshold=100000)
        
        # 主板风险较低
        result_main = classifier.classify(
            symbol="sh.600000", side="buy", quantity=100, price=10.0,
            board_type="主板", strategy="grid",
        )
        
        # 科创板风险较高
        result_star = classifier.classify(
            symbol="sh.688001", side="buy", quantity=100, price=10.0,
            board_type="科创板", strategy="grid",
        )
        
        # 科创板应更可能被拒绝或风险等级更高
        self.assertGreaterEqual(
            classifier._calculate_risk_score(
                type('obj', (object,), {
                    'total_value': 1000, 'board_type': '科创板',
                    'strategy_type': 'grid', 'side': 'buy',
                    'is_new_stock': False, 'price_change_pct': 0,
                    'volume_ratio': 1, 'turnover_rate': 0,
                    'holding_days': 0, 'profit_rate': 0,
                })()
            ),
            classifier._calculate_risk_score(
                type('obj', (object,), {
                    'total_value': 1000, 'board_type': '主板',
                    'strategy_type': 'grid', 'side': 'buy',
                    'is_new_stock': False, 'price_change_pct': 0,
                    'volume_ratio': 1, 'turnover_rate': 0,
                    'holding_days': 0, 'profit_rate': 0,
                })()
            )
        )


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流"""
        # 初始化所有组件
        engine = PermissionEngine(
            mode=PermissionMode.AUTO,
            grace_period_ms=200.0,
            denial_threshold=3,
        )
        
        matcher = RuleMatcher()
        matcher.add_rules(DefaultRules.get_default_rules())
        
        classifier = TradeClassifier(auto_approve_threshold=10000)
        classifier.add_custom_rule(rule_profit_take_auto_approve)
        
        def classifier_callback(request):
            return classifier.classify(
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                price=request.price or 0,
                strategy=request.strategy,
            )
        
        engine.classifier_callback = classifier_callback
        
        # 测试低风险交易 (应自动批准)
        request1 = PermissionRequest(
            action="trade", symbol="000001", side="buy",
            quantity=100, price=10.0, strategy="grid",
        )
        response1 = engine.check_permission(request1, rule_matcher=matcher)
        self.assertTrue(response1.granted)
        
        # 测试高风险交易 (需要确认)
        request2 = PermissionRequest(
            action="trade", symbol="300001", side="buy",
            quantity=500, price=50.0, strategy="momentum",
        )
        response2 = engine.check_permission(request2, rule_matcher=matcher)
        self.assertFalse(response2.granted)
        self.assertTrue(response2.requires_confirmation)
        
        # 用户确认
        engine.confirm_permission(request2, confirmed=True)
        
        # 确认后的请求应重置拒绝计数
        key = f"{request2.action}:{request2.symbol}"
        self.assertEqual(engine.denial_tracker.get_denial_count(key), 0)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestPermissionEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestGracePeriod))
    suite.addTests(loader.loadTestsFromTestCase(TestDenialTracker))
    suite.addTests(loader.loadTestsFromTestCase(TestRuleMatcher))
    suite.addTests(loader.loadTestsFromTestCase(TestTradeClassifier))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回结果
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
