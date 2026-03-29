# ==========================================
# 中频交易模拟盘 - Cron 定时任务配置
# ==========================================

# 查看当前 cron 任务
crontab -l

# 编辑 cron 任务
crontab -e

# ==========================================
# 方案 1: 每 5 分钟检查一次 (交易时段)
# ==========================================
# 周一至周五，9:25-11:35 和 12:55-15:05
*/5 9-11 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
*/5 12-14 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1

# ==========================================
# 方案 2: 每 15 分钟检查一次 (降低频率)
# ==========================================
*/15 9-11 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
*/15 12-14 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1

# ==========================================
# 方案 3: 整点检查 (最低频率)
# ==========================================
0 10 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
0 11 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
0 14 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1

# ==========================================
# 方案 4: 每日报告 (收盘后)
# ==========================================
0 15 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --report >> logs/mf_report.log 2>&1

# ==========================================
# 完整配置示例 (复制以下内容到 crontab)
# ==========================================

# 中频交易模拟盘 - 每 5 分钟检查
*/5 9-11 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
*/5 12-14 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1

# 每日收盘报告
0 15 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --report >> logs/mf_report.log 2>&1

# 每周总结 (周五 15:30)
30 15 * * 5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/weekly_summary.py >> logs/mf_weekly.log 2>&1

# ==========================================
# 管理命令
# ==========================================

# 查看 cron 日志
grep CRON /var/log/syslog | tail -20

# 查看任务执行日志
tail -f logs/mf_sim.log

# 暂停 cron 任务 (注释掉)
# */5 9-11 * * 1-5 ...

# 恢复 cron 任务 (取消注释)
*/5 9-11 * * 1-5 ...

# 删除所有 cron 任务
crontab -r

# 备份 cron 任务
crontab -l > cron_backup.txt

# 恢复 cron 任务
crontab cron_backup.txt

# ==========================================
# 注意事项
# ==========================================
# 1. 确保 Python 路径正确：which python3
# 2. 确保日志目录存在：mkdir -p logs
# 3. 周末休市，无需运行
# 4. 节假日需要手动暂停
# 5. 定期检查日志文件大小
