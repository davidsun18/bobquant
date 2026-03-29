# 🚀 自动运行配置指南

**配置时间**: 2026-03-29  
**状态**: ✅ 已就绪

---

## 🎯 配置目标

让以下两个策略**自动运行**：

1. **日线策略** - 每日 3 次检查 (09:25, 13:00, 15:05)
2. **中频交易** - 每 5 分钟检查 (交易时段)

---

## ⚡ 一键配置 (推荐)

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies

# 执行配置脚本
./setup_cron.sh
```

脚本会自动：
- ✅ 备份现有 Cron 任务
- ✅ 创建日志目录
- ✅ 安装 Cron 任务
- ✅ 验证配置

---

## 🔧 手动配置

### 1. 编辑 Crontab

```bash
crontab -e
```

### 2. 添加以下任务

```bash
# ========== 日线策略 ==========

# V2 自动交易 (09:00, 14:00)
0 9 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 auto_trade_v2.py >> logs/auto_trade.log 2>&1
0 14 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 auto_trade_v2.py >> logs/auto_trade.log 2>&1

# 日线主进程 (09:25, 13:00, 15:05)
25 9 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation >> logs/bobquant.log 2>&1
0 13 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation >> logs/bobquant.log 2>&1
5 15 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation >> logs/bobquant.log 2>&1

# ========== 中频交易 ==========

# 早盘 (9:00-11:00, 每 5 分钟)
*/5 9 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
*/5 10 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
*/5 11 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1

# 午盘 (13:00-15:00, 每 5 分钟)
*/5 13 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
*/5 14 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
0-5/5 15 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1

# ========== 监控与报告 ==========

# 合并报告 (每日 15:30)
30 15 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/start_sim_trading.py --report >> logs/combined_report.log 2>&1

# 状态检查 (每周一 08:00)
0 8 * * 1 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/start_sim_trading.py --status >> logs/weekly_status.log 2>&1

# 日志清理 (每周日 23:00)
0 23 * * 0 find /home/openclaw/.openclaw/workspace/quant_strategies/logs -name "*.log" -mtime +30 -delete

# ========== 开机自启动 ==========

@reboot /home/openclaw/.openclaw/workspace/quant_strategies/start_all.sh
```

### 3. 保存并退出

`:wq` (Vi/Vim) 或 `Ctrl+X` (Nano)

---

## ✅ 验证配置

### 查看已配置的任务

```bash
crontab -l
```

### 查看任务数量

```bash
crontab -l | grep -c "quant_strategies"
```

### 手动测试

```bash
# 测试日线策略
python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation

# 测试中频交易
python3 scripts/run_sim_test.py --run --once

# 查看系统状态
python3 scripts/start_sim_trading.py --status
```

---

## 📊 运行时间表

### 日线策略

| 时间 | 任务 | 说明 |
|------|------|------|
| 09:00 | 自动交易 | 执行减仓/建仓 |
| 09:25 | 主进程检查 | 开盘后检查 |
| 13:00 | 主进程检查 | 午后检查 |
| 14:00 | 自动交易 | 风控检查 |
| 15:05 | 主进程检查 | 收盘检查 |

### 中频交易

| 时段 | 频率 | 说明 |
|------|------|------|
| 09:00-11:30 | 每 5 分钟 | 早盘监控 |
| 13:00-15:00 | 每 5 分钟 | 午盘监控 |
| 周末 | 不运行 | 休市 |

### 监控报告

| 时间 | 任务 | 说明 |
|------|------|------|
| 15:30 (每日) | 合并报告 | 生成日报 |
| 08:00 (周一) | 状态检查 | 周初检查 |
| 23:00 (周日) | 日志清理 | 删除 30 天前日志 |

---

## 📝 日志管理

### 日志文件位置

```
logs/
├── auto_trade.log        # 日线自动交易
├── bobquant.log          # 日线策略
├── mf_sim.log            # 中频交易
├── combined_report.log   # 合并报告
└── weekly_status.log     # 周状态
```

### 查看日志

```bash
# 实时查看
tail -f logs/mf_sim.log

# 查看最近 100 行
tail -n 100 logs/bobquant.log

# 搜索错误
grep "ERROR" logs/mf_sim.log

# 查看今日日志
grep "$(date +%Y-%m-%d)" logs/mf_sim.log
```

### 日志清理

```bash
# 手动清理 (删除 30 天前日志)
find logs/ -name "*.log" -mtime +30 -delete

# 查看日志大小
du -sh logs/
```

---

## ⚠️ 注意事项

### 1. 周末休市
- Cron 只在**周一 - 周五**运行
- 周末和节假日不执行

### 2. 节假日调整
```bash
# 临时禁用 Cron
crontab -r

# 恢复 Cron
crontab /path/to/cron_jobs.txt
```

### 3. Cron 服务状态
```bash
# 查看状态
sudo systemctl status cron

# 重启服务
sudo systemctl restart cron

# 查看 Cron 日志
grep CRON /var/log/syslog | tail -20
```

### 4. 权限问题
```bash
# 确保脚本可执行
chmod +x scripts/*.py
chmod +x setup_cron.sh
```

### 5. Python 路径
```bash
# 检查 Python 路径
which python3

# 如果路径不同，修改 Cron 中的 python3 为完整路径
# 例如：/usr/bin/python3
```

---

## 🔧 故障排查

### 问题 1: Cron 不执行

```bash
# 检查 Cron 服务
sudo systemctl status cron

# 查看 Cron 日志
grep CRON /var/log/syslog | tail -20

# 检查路径
which python3
which crontab
```

### 问题 2: 日志为空

```bash
# 检查日志目录
ls -la logs/

# 手动运行一次
python3 scripts/run_sim_test.py --run --once

# 检查权限
chmod 644 logs/*.log
```

### 问题 3: 任务重复执行

```bash
# 查看已安装的任务
crontab -l

# 删除重复任务
crontab -e

# 或者重置
crontab -r
crontab /path/to/cron_jobs.txt
```

---

## 📞 管理命令汇总

```bash
# 查看任务
crontab -l

# 编辑任务
crontab -e

# 删除所有任务
crontab -r

# 备份任务
crontab -l > backup.txt

# 恢复任务
crontab backup.txt

# 查看 Cron 服务
sudo systemctl status cron

# 重启 Cron 服务
sudo systemctl restart cron

# 查看日志
tail -f logs/mf_sim.log

# 测试中频交易
python3 scripts/run_sim_test.py --run --once

# 查看系统状态
python3 scripts/start_sim_trading.py --status
```

---

## 🎯 配置完成检查清单

- [ ] Cron 任务已配置 (`crontab -l`)
- [ ] 日志目录已创建 (`ls -la logs/`)
- [ ] 手动测试通过 (`python3 scripts/run_sim_test.py --run --once`)
- [ ] Cron 服务运行中 (`sudo systemctl status cron`)
- [ ] 备份文件已创建 (`ls cron_backup_*.txt`)

---

**配置完成时间**: 2026-03-29  
**下次运行时间**: 2026-03-31 09:25 (周一开盘)  
**状态**: ✅ 已就绪
