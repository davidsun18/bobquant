# ==========================================
# 统一模拟盘系统 - Cron 定时任务配置
# ==========================================
# 配置时间：2026-03-29
# 功能：日线策略 + 中频交易 自动运行
# ==========================================

# 查看当前任务
crontab -l

# 编辑任务
crontab -e

# ==========================================
# 现有任务 (保留)
# ==========================================

# V2 策略自动交易 (周一 - 周五)
0 9 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 auto_trade_v2.py >> logs/auto_trade.log 2>&1
0 14 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 auto_trade_v2.py >> logs/auto_trade.log 2>&1

# 开机自启动
@reboot /home/openclaw/.openclaw/workspace/quant_strategies/start_all.sh

# ==========================================
# 新增：日线策略 (bobquant 主进程)
# ==========================================

# 日线策略 - 每日 09:25 启动 (开盘前)
25 9 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation >> logs/bobquant.log 2>&1

# 日线策略 - 午后检查 (13:00)
0 13 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation >> logs/bobquant.log 2>&1

# 日线策略 - 收盘检查 (15:05)
5 15 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation >> logs/bobquant.log 2>&1

# ==========================================
# 新增：中频交易 (每 5 分钟检查)
# ==========================================

# 中频交易 - 早盘 (9:25-11:35, 每 5 分钟)
*/5 9 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
*/5 10 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
*/5 11 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1

# 中频交易 - 午盘 (13:00-15:05, 每 5 分钟)
*/5 13 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
*/5 14 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
0-5/5 15 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1

# ==========================================
# 新增：统一监控与报告
# ==========================================

# 合并报告 - 每日收盘后 (15:30)
30 15 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/start_sim_trading.py --report >> logs/combined_report.log 2>&1

# 系统状态检查 - 每周一 08:00
0 8 * * 1 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/start_sim_trading.py --status >> logs/weekly_status.log 2>&1

# 日志清理 - 每周日 23:00 (保留最近 30 天)
0 23 * * 0 find /home/openclaw/.openclaw/workspace/quant_strategies/logs -name "*.log" -mtime +30 -delete

# ==========================================
# 完整配置 (复制以下内容到 crontab)
# ==========================================

# V2 策略自动交易 (周一 - 周五)
0 9 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 auto_trade_v2.py >> logs/auto_trade.log 2>&1
0 14 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 auto_trade_v2.py >> logs/auto_trade.log 2>&1

# 开机自启动
@reboot /home/openclaw/.openclaw/workspace/quant_strategies/start_all.sh

# 日线策略 (bobquant 主进程)
25 9 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation >> logs/bobquant.log 2>&1
0 13 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation >> logs/bobquant.log 2>&1
5 15 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation >> logs/bobquant.log 2>&1

# 中频交易 (每 5 分钟检查)
*/5 9 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
*/5 10 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
*/5 11 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
*/5 13 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
*/5 14 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1
0-5/5 15 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/run_sim_test.py --run --once >> logs/mf_sim.log 2>&1

# 统一监控与报告
30 15 * * 1-5 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/start_sim_trading.py --report >> logs/combined_report.log 2>&1
0 8 * * 1 cd /home/openclaw/.openclaw/workspace/quant_strategies && python3 scripts/start_sim_trading.py --status >> logs/weekly_status.log 2>&1

# 日志清理
0 23 * * 0 find /home/openclaw/.openclaw/workspace/quant_strategies/logs -name "*.log" -mtime +30 -delete

# ==========================================
# 管理命令
# ==========================================

# 查看 Cron 任务
crontab -l

# 编辑 Cron 任务
crontab -e

# 查看 Cron 日志
grep CRON /var/log/syslog | tail -20

# 查看任务执行日志
tail -f logs/auto_trade.log      # 日线自动交易
tail -f logs/bobquant.log        # 日线策略
tail -f logs/mf_sim.log          # 中频交易
tail -f logs/combined_report.log # 合并报告

# 暂停 Cron 任务 (注释掉)
# */5 9 * * 1-5 ...

# 恢复 Cron 任务 (取消注释)
*/5 9 * * 1-5 ...

# 删除所有 Cron 任务
crontab -r

# 备份 Cron 任务
crontab -l > cron_backup.txt

# 恢复 Cron 任务
crontab cron_backup.txt

# ==========================================
# 注意事项
# ==========================================
# 1. 确保 Python 路径正确：which python3
# 2. 确保日志目录存在：mkdir -p logs
# 3. 周末休市，Cron 只在周一 - 周五运行
# 4. 节假日需要手动暂停
# 5. 定期检查日志文件大小
# 6. 确保账户文件存在且有权限

# ==========================================
# 验证配置
# ==========================================

# 1. 查看已配置的 Cron 任务
crontab -l | grep -E "quant_strategies"

# 2. 手动测试日线策略
cd /home/openclaw/.openclaw/workspace/quant_strategies
python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation

# 3. 手动测试中频交易
cd /home/openclaw/.openclaw/workspace/quant_strategies
python3 scripts/run_sim_test.py --run --once

# 4. 查看 Cron 服务状态
sudo systemctl status cron

# 5. 重启 Cron 服务 (如有问题)
sudo systemctl restart cron
