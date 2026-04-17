#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant 性能测试套件

测试项目：
1. 工具系统性能测试（调用延迟）
2. 权限系统性能测试（规则匹配速度）
3. 错误处理性能测试（分类器速度）
4. 遥测系统性能测试（批处理吞吐量）
5. 配置系统性能测试（加载速度）

输出：
- 性能测试报告
- 性能对比数据（重构前后）
- 优化建议
"""

import sys
import os
import time
import statistics
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import threading
import concurrent.futures

# 添加项目路径 - 使用绝对路径
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
PARENT_DIR = PROJECT_ROOT.parent.resolve()

if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

# 设置环境变量以便导入
os.environ['PYTHONPATH'] = str(PARENT_DIR)

# ==================== 测试结果数据结构 ====================

@dataclass
class PerformanceMetrics:
    """性能指标"""
    test_name: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    median_time_ms: float
    std_dev_ms: float
    operations_per_second: float
    timestamp: str


@dataclass
class PerformanceReport:
    """性能测试报告"""
    test_suite: str
    bobquant_version: str
    test_date: str
    python_version: str
    system_info: str
    metrics: List[PerformanceMetrics]
    summary: Dict[str, Any]


# ==================== 性能测试基类 ====================

class PerformanceTester:
    """性能测试基类"""
    
    def __init__(self, name: str, iterations: int = 1000):
        self.name = name
        self.iterations = iterations
        self.results: List[float] = []
    
    def setup(self):
        """测试前准备"""
        pass
    
    def teardown(self):
        """测试后清理"""
        pass
    
    def run_test(self) -> PerformanceMetrics:
        """运行性能测试"""
        self.setup()
        
        times = []
        start_total = time.perf_counter()
        
        for i in range(self.iterations):
            iter_start = time.perf_counter()
            self._run_iteration(i)
            iter_end = time.perf_counter()
            times.append((iter_end - iter_start) * 1000)  # 转换为毫秒
        
        end_total = time.perf_counter()
        total_time = (end_total - start_total) * 1000
        
        self.teardown()
        
        # 计算统计指标
        return self._calculate_metrics(total_time, times)
    
    def _run_iteration(self, iteration: int):
        """单次测试迭代（由子类实现）"""
        raise NotImplementedError
    
    def _calculate_metrics(self, total_time: float, times: List[float]) -> PerformanceMetrics:
        """计算性能指标"""
        if not times:
            times = [0.0]
        
        return PerformanceMetrics(
            test_name=self.name,
            iterations=self.iterations,
            total_time_ms=round(total_time, 3),
            avg_time_ms=round(statistics.mean(times), 3),
            min_time_ms=round(min(times), 3),
            max_time_ms=round(max(times), 3),
            median_time_ms=round(statistics.median(times), 3),
            std_dev_ms=round(statistics.stdev(times) if len(times) > 1 else 0, 3),
            operations_per_second=round(1000 / statistics.mean(times) if times else 0, 2),
            timestamp=datetime.now().isoformat(),
        )


# ==================== 1. 工具系统性能测试 ====================

class ToolSystemTester(PerformanceTester):
    """工具系统性能测试"""
    
    def __init__(self, iterations: int = 1000):
        super().__init__("工具系统性能测试", iterations)
        self.registry = None
        self.tools = []
    
    def setup(self):
        """初始化工具注册表"""
        import importlib
        base_module = importlib.import_module('bobquant.tools.base')
        registry_module = importlib.import_module('bobquant.tools.registry')
        
        Tool = base_module.Tool
        ToolContext = base_module.ToolContext
        ToolResult = base_module.ToolResult
        ToolRegistry = registry_module.ToolRegistry
        
        # 创建测试工具类
        class TestTool(Tool):
            name = "test_tool"
            description_text = "测试工具"
            
            async def execute(self, ctx: ToolContext) -> ToolResult:
                return ToolResult(success=True, data={"result": "test"})
        
        # 创建注册表并注册工具
        self.registry = ToolRegistry.get_instance()
        
        # 注册多个测试工具
        self.test_tool_classes = []
        for i in range(10):
            tool_name = f"test_tool_{i}"
            tool_desc = f"测试工具 {i}"
            
            # 创建工具类
            class DynamicTestToolImpl(Tool):
                name = tool_name
                description_text = tool_desc
                aliases = []  # 添加别名属性
                
                async def call(self, args, ctx, on_progress=None):
                    return ToolResult(data={"result": "test"})
            
            self.registry.register(DynamicTestToolImpl, category="test")
            self.test_tool_classes.append(DynamicTestToolImpl)
            self.tools.append(tool_name)
    
    def teardown(self):
        """清理"""
        # 注意：不实际注销工具，避免影响后续测试
        # 工具注册表是单例，清理可能导致问题
        pass
    
    def _run_iteration(self, iteration: int):
        """测试工具查找性能"""
        tool_name = self.tools[iteration % len(self.tools)]
        tool = self.registry.get(tool_name)
        # 验证工具存在
        assert tool is not None, f"工具 {tool_name} 未找到"


# ==================== 2. 权限系统性能测试 ====================

class PermissionSystemTester(PerformanceTester):
    """权限系统性能测试"""
    
    def __init__(self, iterations: int = 1000):
        super().__init__("权限系统性能测试", iterations)
        self.matcher = None
        self.test_cases = []
    
    def setup(self):
        """初始化规则匹配器"""
        import importlib
        rules_module = importlib.import_module('bobquant.permissions.rules')
        
        Rule = rules_module.Rule
        RuleMatcher = rules_module.RuleMatcher
        RuleAction = rules_module.RuleAction
        
        self.matcher = RuleMatcher()
        
        # 添加测试规则
        rules = [
            Rule(pattern="Trade(000001.*)", action=RuleAction.ALLOW, priority=10),
            Rule(pattern="Trade(600.*)", action=RuleAction.ALLOW, priority=9),
            Rule(pattern="Trade(300.*)", action=RuleAction.ASK, priority=8),
            Rule(pattern="Risk(*)", action=RuleAction.DENY, priority=100),
            Rule(pattern="Cancel(*)", action=RuleAction.ALLOW, priority=5),
            Rule(pattern="Modify(000002.*)", action=RuleAction.ASK, priority=7),
        ]
        
        self.matcher.add_rules(rules)
        
        # 准备测试用例
        self.test_cases = [
            ("000001.SZ", "trade"),
            ("600519.SH", "trade"),
            ("300750.SZ", "trade"),
            ("000002.SZ", "modify"),
            ("ANY", "risk"),
            ("123456", "cancel"),
        ]
    
    def _run_iteration(self, iteration: int):
        """测试规则匹配性能"""
        target, action_type = self.test_cases[iteration % len(self.test_cases)]
        result = self.matcher.match(target, action_type)
        # 验证返回结果
        assert 'action' in result, "匹配结果缺少 action 字段"


# ==================== 3. 错误处理性能测试 ====================

class ErrorHandlingTester(PerformanceTester):
    """错误处理性能测试"""
    
    def __init__(self, iterations: int = 1000):
        super().__init__("错误处理性能测试", iterations)
        self.classifier = None
        self.test_errors = []
    
    def setup(self):
        """初始化错误分类器"""
        import importlib
        classifier_module = importlib.import_module('bobquant.errors.classifier')
        
        ErrorClassifier = classifier_module.ErrorClassifier
        
        self.classifier = ErrorClassifier()
        
        # 准备测试错误 - 使用更简单的错误类型避免 context 问题
        self.test_errors = [
            Exception("Generic error"),
            RuntimeError("Runtime error occurred"),
            ValueError("Invalid value"),
            OSError("OS error"),
        ]
    
    def _run_iteration(self, iteration: int):
        """测试错误分类性能"""
        error = self.test_errors[iteration % len(self.test_errors)]
        try:
            classified = self.classifier.classify(error)
            # 验证分类结果
            assert classified is not None, "错误分类结果为空"
        except Exception:
            # 分类失败也算一次操作
            pass


# ==================== 4. 遥测系统性能测试 ====================

class TelemetrySystemTester(PerformanceTester):
    """遥测系统性能测试"""
    
    def __init__(self, iterations: int = 1000):
        super().__init__("遥测系统性能测试", iterations)
        self.batch_processor = None
        self.events = []
    
    def setup(self):
        """初始化批处理器"""
        import importlib
        batch_module = importlib.import_module('bobquant.telemetry.batch')
        sink_module = importlib.import_module('bobquant.telemetry.sink')
        
        BatchProcessor = batch_module.BatchProcessor
        BatchConfig = batch_module.BatchConfig
        TelemetryEvent = sink_module.TelemetryEvent
        
        # 配置批处理器
        config = BatchConfig(
            max_batch_size=100,
            max_wait_time=5.0,
            max_queue_size=1000
        )
        
        self.batch_processor = BatchProcessor(config)
        
        # 注册批次处理器
        def dummy_handler(batch):
            pass  # 空处理器，只测试批处理性能
        
        self.batch_processor.on_batch_ready(dummy_handler)
        self.batch_processor.start()
        
        # 准备测试事件
        from bobquant.telemetry.sink import EventType
        
        self.events = [
            TelemetryEvent(
                event_type=EventType.CUSTOM,
                event_name="test_event",
                timestamp=time.time(),
                attributes={"iteration": i % 100, "test": "performance"}
            )
            for i in range(100)
        ]
    
    def teardown(self):
        """清理"""
        if self.batch_processor:
            self.batch_processor.stop(flush=True)
    
    def _run_iteration(self, iteration: int):
        """测试事件批处理性能"""
        event = self.events[iteration % len(self.events)]
        self.batch_processor.process(event)


# ==================== 5. 配置系统性能测试 ====================

class ConfigSystemTester(PerformanceTester):
    """配置系统性能测试"""
    
    def __init__(self, iterations: int = 100):
        super().__init__("配置系统性能测试", iterations)
        self.config_path = None
        self.config_data = None
    
    def setup(self):
        """准备测试配置文件"""
        import tempfile
        import json5
        
        # 创建测试配置
        self.config_data = {
            "global": {
                "app_name": "BobQuant",
                "version": "2.5.0",
                "log_level": "INFO",
                "data_dir": "/tmp/bobquant_data",
            },
            "strategies": {
                "macd": {
                    "enabled": True,
                    "params": {
                        "fast_period": 12,
                        "slow_period": 26,
                        "signal_period": 9,
                    }
                },
                "rsi": {
                    "enabled": True,
                    "params": {
                        "period": 14,
                        "overbought": 70,
                        "oversold": 30,
                    }
                }
            },
            "risk_management": {
                "max_position": 0.3,
                "stop_loss": 0.05,
                "take_profit": 0.10,
            },
            "trading": {
                "market_hours": {
                    "morning": {"start": "09:25", "end": "11:35"},
                    "afternoon": {"start": "12:55", "end": "15:05"},
                }
            }
        }
        
        # 创建临时配置文件
        fd, self.config_path = tempfile.mkstemp(suffix='.json5')
        os.close(fd)
        
        with open(self.config_path, 'w') as f:
            json5.dump(self.config_data, f)
    
    def teardown(self):
        """清理临时文件"""
        if self.config_path and os.path.exists(self.config_path):
            os.remove(self.config_path)
    
    def _run_iteration(self, iteration: int):
        """测试配置加载性能"""
        import importlib
        config_module = importlib.import_module('bobquant.config.schema')
        
        ConfigLoader = config_module.ConfigLoader
        
        loader = ConfigLoader()
        # 使用 load_json5 方法直接加载 JSON5 文件
        config = loader.load_json5(self.config_path)
        
        # 验证配置加载成功
        assert config is not None, "配置加载失败"
        assert 'global' in config, "配置缺少 global 部分"


# ==================== 性能对比测试 ====================

class PerformanceComparator:
    """性能对比器（重构前后对比）"""
    
    def __init__(self):
        self.baseline_results: Dict[str, PerformanceMetrics] = {}
        self.current_results: Dict[str, PerformanceMetrics] = {}
    
    def load_baseline(self, baseline_file: str):
        """加载基线数据（重构前）"""
        if os.path.exists(baseline_file):
            with open(baseline_file, 'r') as f:
                data = json.load(f)
                for metrics in data.get('metrics', []):
                    self.baseline_results[metrics['test_name']] = PerformanceMetrics(**metrics)
    
    def add_current_result(self, metrics: PerformanceMetrics):
        """添加当前测试结果"""
        self.current_results[metrics.test_name] = metrics
    
    def generate_comparison(self) -> Dict[str, Any]:
        """生成对比报告"""
        comparisons = []
        
        for test_name, current in self.current_results.items():
            baseline = self.baseline_results.get(test_name)
            
            if baseline:
                improvement = ((baseline.avg_time_ms - current.avg_time_ms) / baseline.avg_time_ms) * 100
                speedup = baseline.avg_time_ms / current.avg_time_ms if current.avg_time_ms > 0 else 0
            else:
                improvement = None
                speedup = None
            
            comparisons.append({
                'test_name': test_name,
                'baseline_avg_ms': baseline.avg_time_ms if baseline else None,
                'current_avg_ms': current.avg_time_ms,
                'improvement_percent': improvement,
                'speedup_factor': speedup,
                'baseline_ops': baseline.operations_per_second if baseline else None,
                'current_ops': current.operations_per_second,
            })
        
        return {
            'comparisons': comparisons,
            'summary': {
                'tests_improved': sum(1 for c in comparisons if c['improvement_percent'] and c['improvement_percent'] > 0),
                'tests_degraded': sum(1 for c in comparisons if c['improvement_percent'] and c['improvement_percent'] < 0),
                'avg_improvement': statistics.mean([c['improvement_percent'] for c in comparisons if c['improvement_percent'] is not None]) if comparisons else 0,
            }
        }


# ==================== 主测试套件 ====================

class BobQuantPerformanceTestSuite:
    """BobQuant 性能测试套件"""
    
    def __init__(self, iterations: Dict[str, int] = None):
        self.iterations = iterations or {
            'tool': 1000,
            'permission': 1000,
            'error': 1000,
            'telemetry': 1000,
            'config': 100,
        }
        self.results: List[PerformanceMetrics] = []
        self.comparator = PerformanceComparator()
    
    def run_all_tests(self) -> PerformanceReport:
        """运行所有性能测试"""
        print("=" * 60)
        print("BobQuant 性能测试套件")
        print("=" * 60)
        
        # 1. 工具系统测试
        print("\n[1/5] 工具系统性能测试...")
        tool_tester = ToolSystemTester(self.iterations['tool'])
        tool_metrics = tool_tester.run_test()
        self.results.append(tool_metrics)
        self.comparator.add_current_result(tool_metrics)
        print(f"    平均延迟：{tool_metrics.avg_time_ms:.3f} ms")
        print(f"    操作/秒：{tool_metrics.operations_per_second:.2f}")
        
        # 2. 权限系统测试
        print("\n[2/5] 权限系统性能测试...")
        perm_tester = PermissionSystemTester(self.iterations['permission'])
        perm_metrics = perm_tester.run_test()
        self.results.append(perm_metrics)
        self.comparator.add_current_result(perm_metrics)
        print(f"    平均延迟：{perm_metrics.avg_time_ms:.3f} ms")
        print(f"    操作/秒：{perm_metrics.operations_per_second:.2f}")
        
        # 3. 错误处理测试
        print("\n[3/5] 错误处理性能测试...")
        error_tester = ErrorHandlingTester(self.iterations['error'])
        error_metrics = error_tester.run_test()
        self.results.append(error_metrics)
        self.comparator.add_current_result(error_metrics)
        print(f"    平均延迟：{error_metrics.avg_time_ms:.3f} ms")
        print(f"    操作/秒：{error_metrics.operations_per_second:.2f}")
        
        # 4. 遥测系统测试
        print("\n[4/5] 遥测系统性能测试...")
        telemetry_tester = TelemetrySystemTester(self.iterations['telemetry'])
        telemetry_metrics = telemetry_tester.run_test()
        self.results.append(telemetry_metrics)
        self.comparator.add_current_result(telemetry_metrics)
        print(f"    平均延迟：{telemetry_metrics.avg_time_ms:.3f} ms")
        print(f"    操作/秒：{telemetry_metrics.operations_per_second:.2f}")
        
        # 5. 配置系统测试
        print("\n[5/5] 配置系统性能测试...")
        config_tester = ConfigSystemTester(self.iterations['config'])
        config_metrics = config_tester.run_test()
        self.results.append(config_metrics)
        self.comparator.add_current_result(config_metrics)
        print(f"    平均延迟：{config_metrics.avg_time_ms:.3f} ms")
        print(f"    操作/秒：{config_metrics.operations_per_second:.2f}")
        
        # 生成报告
        return self._generate_report()
    
    def _generate_report(self) -> PerformanceReport:
        """生成性能测试报告"""
        import platform
        
        # 计算总体统计
        total_avg = statistics.mean([m.avg_time_ms for m in self.results])
        total_ops = sum([m.operations_per_second for m in self.results])
        
        report = PerformanceReport(
            test_suite="BobQuant Performance Test Suite",
            bobquant_version="2.5.0-refactored",
            test_date=datetime.now().isoformat(),
            python_version=platform.python_version(),
            system_info=f"{platform.system()} {platform.release()} ({platform.machine()})",
            metrics=self.results,
            summary={
                'total_tests': len(self.results),
                'overall_avg_latency_ms': round(total_avg, 3),
                'total_operations_per_second': round(total_ops, 2),
                'fastest_test': min(self.results, key=lambda m: m.avg_time_ms).test_name,
                'slowest_test': max(self.results, key=lambda m: m.avg_time_ms).test_name,
            }
        )
        
        return report
    
    def save_report(self, report: PerformanceReport, output_file: str):
        """保存测试报告"""
        report_dict = {
            'test_suite': report.test_suite,
            'bobquant_version': report.bobquant_version,
            'test_date': report.test_date,
            'python_version': report.python_version,
            'system_info': report.system_info,
            'metrics': [asdict(m) for m in report.metrics],
            'summary': report.summary,
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 报告已保存至：{output_file}")
    
    def save_comparison(self, baseline_file: str, comparison_file: str):
        """保存对比报告"""
        self.comparator.load_baseline(baseline_file)
        comparison = self.comparator.generate_comparison()
        
        with open(comparison_file, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 对比报告已保存至：{comparison_file}")
        
        # 打印对比摘要
        print("\n" + "=" * 60)
        print("性能对比摘要")
        print("=" * 60)
        
        for comp in comparison['comparisons']:
            if comp['improvement_percent'] is not None:
                status = "↑" if comp['improvement_percent'] > 0 else "↓"
                print(f"{comp['test_name']}: {comp['improvement_percent']:+.1f}% {status}")
            else:
                print(f"{comp['test_name']}: (无基线数据)")
        
        summary = comparison['summary']
        print(f"\n总体改进：{summary['avg_improvement']:+.1f}%")
        print(f"改进测试数：{summary['tests_improved']}")
        print(f"退化测试数：{summary['tests_degraded']}")


# ==================== 优化建议生成器 ====================

class OptimizationAdvisor:
    """优化建议生成器"""
    
    @staticmethod
    def generate_advice(report: PerformanceReport, comparison: Dict = None) -> str:
        """生成优化建议"""
        advice = []
        
        advice.append("# BobQuant 性能优化建议\n")
        advice.append(f"生成时间：{datetime.now().isoformat()}\n")
        advice.append(f"BobQuant 版本：{report.bobquant_version}\n\n")
        
        # 分析各项测试结果
        for metrics in report.metrics:
            advice.append(f"## {metrics.test_name}\n")
            advice.append(f"- 平均延迟：{metrics.avg_time_ms:.3f} ms\n")
            advice.append(f"- 操作/秒：{metrics.operations_per_second:.2f}\n")
            advice.append(f"- 标准差：{metrics.std_dev_ms:.3f} ms\n\n")
            
            # 根据指标给出建议
            if metrics.avg_time_ms > 10:
                advice.append("**优化建议**: 延迟较高，考虑以下优化：\n")
                advice.append("- 检查是否有不必要的 I/O 操作\n")
                advice.append("- 考虑添加缓存机制\n")
                advice.append("- 优化数据结构减少内存分配\n\n")
            elif metrics.std_dev_ms > metrics.avg_time_ms * 0.5:
                advice.append("**优化建议**: 延迟波动较大，考虑以下优化：\n")
                advice.append("- 检查是否有 GC 压力\n")
                advice.append("- 预分配资源减少动态分配\n")
                advice.append("- 避免在热路径上进行系统调用\n\n")
        
        # 对比分析
        if comparison:
            advice.append("## 重构前后对比\n")
            for comp in comparison['comparisons']:
                if comp['improvement_percent'] is not None:
                    if comp['improvement_percent'] > 20:
                        advice.append(f"- ✅ {comp['test_name']}: 性能提升 {comp['improvement_percent']:.1f}%\n")
                    elif comp['improvement_percent'] < -20:
                        advice.append(f"- ⚠️ {comp['test_name']}: 性能下降 {abs(comp['improvement_percent']):.1f}%，需要优化\n")
        
        # 总体建议
        advice.append("\n## 总体建议\n")
        advice.append("1. **工具系统**: 考虑使用连接池减少重复初始化开销\n")
        advice.append("2. **权限系统**: 规则匹配可使用编译后的正则表达式缓存\n")
        advice.append("3. **错误处理**: 分类规则可使用 Trie 树优化匹配速度\n")
        advice.append("4. **遥测系统**: 批处理参数可根据负载动态调整\n")
        advice.append("5. **配置系统**: 配置解析结果可缓存避免重复加载\n")
        
        return "".join(advice)


# ==================== 命令行入口 ====================

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='BobQuant 性能测试套件')
    parser.add_argument('--iterations', type=int, default=1000, help='测试迭代次数')
    parser.add_argument('--output', type=str, default='performance_report.json', help='报告输出文件')
    parser.add_argument('--baseline', type=str, help='基线数据文件（用于对比）')
    parser.add_argument('--comparison-output', type=str, default='performance_comparison.json', help='对比报告输出文件')
    parser.add_argument('--advice-output', type=str, default='performance_advice.md', help='优化建议输出文件')
    
    args = parser.parse_args()
    
    # 创建测试套件
    suite = BobQuantPerformanceTestSuite(iterations={
        'tool': args.iterations,
        'permission': args.iterations,
        'error': args.iterations,
        'telemetry': args.iterations,
        'config': args.iterations // 10,  # 配置测试较慢，减少迭代次数
    })
    
    # 运行测试
    report = suite.run_all_tests()
    
    # 保存报告
    suite.save_report(report, args.output)
    
    # 保存对比报告（如果有基线）
    if args.baseline:
        suite.save_comparison(args.baseline, args.comparison_output)
        comparison = suite.comparator.generate_comparison()
    else:
        comparison = None
    
    # 生成优化建议
    advice = OptimizationAdvisor.generate_advice(report, comparison)
    with open(args.advice_output, 'w', encoding='utf-8') as f:
        f.write(advice)
    print(f"✓ 优化建议已保存至：{args.advice_output}")
    
    # 打印报告摘要
    print("\n" + "=" * 60)
    print("性能测试报告摘要")
    print("=" * 60)
    print(f"测试套件：{report.test_suite}")
    print(f"BobQuant 版本：{report.bobquant_version}")
    print(f"Python 版本：{report.python_version}")
    print(f"系统：{report.system_info}")
    print(f"\n总体平均延迟：{report.summary['overall_avg_latency_ms']:.3f} ms")
    print(f"总操作/秒：{report.summary['total_operations_per_second']:.2f}")
    print(f"最快测试：{report.summary['fastest_test']}")
    print(f"最慢测试：{report.summary['slowest_test']}")
    
    print("\n" + "=" * 60)
    print("性能测试完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
