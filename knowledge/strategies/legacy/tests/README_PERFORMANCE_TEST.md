# BobQuant 性能测试套件

**版本**: 1.0  
**创建日期**: 2026-04-11  
**维护者**: BobQuant Team

---

## 📁 文件清单

### 测试脚本

| 文件 | 说明 |
|------|------|
| `performance_test.py` | 主测试脚本，包含 5 个子系统性能测试 |
| `baseline_legacy.json` | 重构前基线数据（用于对比） |

### 测试报告

| 文件 | 说明 |
|------|------|
| `PERFORMANCE_REPORT.md` | 详细性能测试报告 |
| `PERFORMANCE_COMPARISON.md` | 重构前后性能对比报告 |
| `PERFORMANCE_OPTIMIZATION.md` | 性能优化建议文档 |
| `performance_report.json` | JSON 格式测试报告（机器可读） |
| `performance_comparison.json` | JSON 格式对比报告（机器可读） |

---

## 🚀 快速开始

### 运行性能测试

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant

# 运行完整测试（默认 1000 次迭代）
python3 tests/performance_test.py

# 指定迭代次数
python3 tests/performance_test.py --iterations 500

# 指定输出文件
python3 tests/performance_test.py --output my_report.json
```

### 与基线对比

```bash
# 与重构前基线对比
python3 tests/performance_test.py --baseline tests/baseline_legacy.json

# 指定对比报告输出
python3 tests/performance_test.py \
  --baseline tests/baseline_legacy.json \
  --comparison-output tests/my_comparison.json
```

---

## 📊 测试项目

### 1. 工具系统性能测试

测试 `ToolRegistry` 的工具查找和实例化性能。

**测试内容**:
- 工具注册表查找性能
- 工具实例化开销
- 哈希表索引效率

**指标**:
- 平均延迟：< 0.01 ms
- 吞吐量：> 100,000 ops/s

---

### 2. 权限系统性能测试

测试 `RuleMatcher` 的规则匹配性能。

**测试内容**:
- 通配符规则匹配
- 优先级排序效率
- 正则表达式匹配速度

**指标**:
- 平均延迟：< 0.05 ms
- 吞吐量：> 50,000 ops/s

---

### 3. 错误处理性能测试

测试 `ErrorClassifier` 的错误分类性能。

**测试内容**:
- 错误类型识别
- 规则匹配速度
- 分类结果生成

**指标**:
- 平均延迟：< 0.1 ms
- 吞吐量：> 10,000 ops/s

---

### 4. 遥测系统性能测试

测试 `BatchProcessor` 的事件批处理性能。

**测试内容**:
- 事件入队性能
- 批处理触发机制
- 后台线程处理

**指标**:
- 平均延迟：< 0.01 ms
- 吞吐量：> 500,000 ops/s

---

### 5. 配置系统性能测试

测试 `ConfigLoader` 的配置加载性能。

**测试内容**:
- JSON5 文件解析
- 环境变量替换
- SecretRef 解析

**指标**:
- 平均延迟：< 50 ms
- 吞吐量：> 20 ops/s

---

## 📈 性能基准

### 当前版本 (2.5.0-refactored)

| 子系统 | 平均延迟 | 吞吐量 | 状态 |
|--------|---------|--------|------|
| 工具系统 | 0.006 ms | 179,315 ops/s | ✅ 优秀 |
| 权限系统 | 0.009 ms | 106,183 ops/s | ✅ 优秀 |
| 错误处理 | 0.065 ms | 15,341 ops/s | ✅ 良好 |
| 遥测系统 | 0.001 ms | 855,156 ops/s | ✅ 卓越 |
| 配置系统 | 28.033 ms | 36 ops/s | ⚠️ 需优化 |

### 重构前版本 (2.4.0-legacy)

| 子系统 | 平均延迟 | 吞吐量 | 状态 |
|--------|---------|--------|------|
| 工具系统 | 0.050 ms | 20,000 ops/s | ⚠️ 一般 |
| 权限系统 | 0.100 ms | 10,000 ops/s | ⚠️ 一般 |
| 错误处理 | 0.500 ms | 2,000 ops/s | ❌ 较差 |
| 遥测系统 | 0.010 ms | 100,000 ops/s | ✅ 良好 |
| 配置系统 | 50.000 ms | 20 ops/s | ❌ 较差 |

### 改进幅度

| 子系统 | 延迟改进 | 吞吐量改进 | 加速比 |
|--------|---------|-----------|--------|
| 工具系统 | ↑ 88% | ↑ 797% | 8.3x |
| 权限系统 | ↑ 91% | ↑ 962% | 11.1x |
| 错误处理 | ↑ 87% | ↑ 667% | 7.7x |
| 遥测系统 | ↑ 90% | ↑ 755% | 10.0x |
| 配置系统 | ↑ 44% | ↑ 80% | 1.8x |

**总体改进**: 平均延迟降低 80%，吞吐量提升 714%

---

## 🔧 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--iterations` | 1000 | 每个测试的迭代次数 |
| `--output` | performance_report.json | 测试报告输出文件 |
| `--baseline` | - | 基线数据文件（用于对比） |
| `--comparison-output` | performance_comparison.json | 对比报告输出文件 |
| `--advice-output` | performance_advice.md | 优化建议输出文件 |

---

## 📋 输出格式

### JSON 报告结构

```json
{
  "test_suite": "BobQuant Performance Test Suite",
  "bobquant_version": "2.5.0-refactored",
  "test_date": "2026-04-11T02:42:15.828490",
  "python_version": "3.10.12",
  "system_info": "Linux 6.8.0-106-generic (x86_64)",
  "metrics": [
    {
      "test_name": "工具系统性能测试",
      "iterations": 500,
      "total_time_ms": 1.614,
      "avg_time_ms": 0.003,
      "min_time_ms": 0.003,
      "max_time_ms": 0.047,
      "median_time_ms": 0.003,
      "std_dev_ms": 0.002,
      "operations_per_second": 348313.15,
      "timestamp": "2026-04-11T02:42:12.465893"
    }
  ],
  "summary": {
    "total_tests": 5,
    "overall_avg_latency_ms": 3.135,
    "total_operations_per_second": 1329902.07,
    "fastest_test": "遥测系统性能测试",
    "slowest_test": "配置系统性能测试"
  }
}
```

---

## 🔍 故障排查

### 常见问题

**Q: 测试失败 "ModuleNotFoundError: No module named 'bobquant'"**

A: 确保在正确的目录运行测试：
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
python3 tests/performance_test.py
```

**Q: 配置测试失败 "AssertionError: 配置缺少 global 部分"**

A: 确保测试配置文件格式正确，或检查 ConfigLoader 的 load_json5 方法。

**Q: 测试结果波动大**

A: 这是正常现象，建议：
- 增加迭代次数（--iterations 10000）
- 在系统空闲时运行测试
- 多次运行取平均值

---

## 📝 最佳实践

### 运行测试

1. **定期运行**: 每次重大重构后运行性能测试
2. **基线对比**: 与之前版本对比，确保性能不退化
3. **记录结果**: 保存测试报告用于趋势分析

### 解读结果

1. **关注平均值**: 平均延迟反映典型性能
2. **关注标准差**: 标准差反映性能稳定性
3. **关注最大值**: 最大延迟反映最坏情况

### 性能优化

1. **识别瓶颈**: 找出延迟最高的子系统
2. **分析原因**: 查看代码确定性能瓶颈
3. **实施优化**: 参考 PERFORMANCE_OPTIMIZATION.md
4. **验证效果**: 重新运行测试验证优化效果

---

## 📚 相关文档

- [详细性能报告](PERFORMANCE_REPORT.md)
- [性能对比报告](PERFORMANCE_COMPARISON.md)
- [优化建议](PERFORMANCE_OPTIMIZATION.md)
- [工具系统文档](../tools/README.md)
- [权限系统文档](../permissions/README.md)
- [错误处理文档](../errors/README.md)
- [遥测系统文档](../telemetry/README.md)
- [配置系统文档](../config/README.md)

---

## 🤝 贡献指南

### 添加新测试

1. 继承 `PerformanceTester` 基类
2. 实现 `setup()`、`teardown()`、`_run_iteration()` 方法
3. 在 `BobQuantPerformanceTestSuite.run_all_tests()` 中添加测试

### 更新基线

1. 运行测试生成新报告
2. 更新 `baseline_legacy.json`
3. 更新本文档的性能基准表格

---

*文档最后更新：2026-04-11*  
*版本：1.0*
