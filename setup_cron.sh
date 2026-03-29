#!/bin/bash
# ==========================================
# 统一模拟盘系统 - Cron 配置脚本
# ==========================================
# 用法：./setup_cron.sh
# 功能：自动配置日线和中频交易的定时任务
# ==========================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_FILE="$SCRIPT_DIR/cron_jobs.txt"
BACKUP_FILE="$SCRIPT_DIR/cron_backup_$(date +%Y%m%d_%H%M%S).txt"

echo "=========================================="
echo "  🤖 统一模拟盘系统 - Cron 配置"
echo "=========================================="
echo ""

# 检查是否在正确的目录
if [ ! -f "$SCRIPT_DIR/web_ui.py" ]; then
    echo "❌ 错误：请在 quant_strategies 目录下运行此脚本"
    exit 1
fi

# 创建日志目录
echo "📁 创建日志目录..."
mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/sim_trading/reports"
echo "  ✅ 日志目录已创建"
echo ""

# 备份现有 Cron 任务
echo "💾 备份现有 Cron 任务..."
if crontab -l > "$BACKUP_FILE" 2>/dev/null; then
    echo "  ✅ 已备份到：$BACKUP_FILE"
else
    echo "  ⚠️  没有现有 Cron 任务"
fi
echo ""

# 创建 Cron 配置文件
echo "📝 创建 Cron 配置文件..."
cat > "$CRON_FILE" << 'EOF'
# ==========================================
# 统一模拟盘系统 - Cron 定时任务
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

# 日志清理 (每周日)
0 23 * * 0 find /home/openclaw/.openclaw/workspace/quant_strategies/logs -name "*.log" -mtime +30 -delete
EOF

echo "  ✅ Cron 配置文件已创建"
echo ""

# 显示要配置的 Cron 任务
echo "📋 将要配置的 Cron 任务:"
echo "----------------------------------------"
cat "$CRON_FILE" | grep -v "^#" | grep -v "^$"
echo "----------------------------------------"
echo ""

# 询问用户确认
read -p "是否继续配置？(y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 已取消配置"
    exit 0
fi

# 安装 Cron 任务
echo "🔧 安装 Cron 任务..."
crontab "$CRON_FILE"
echo "  ✅ Cron 任务已安装"
echo ""

# 验证安装
echo "✅ 验证安装..."
if crontab -l | grep -q "quant_strategies"; then
    echo "  ✅ Cron 任务已成功安装"
    echo ""
    echo "📊 已配置的任务数量:"
    crontab -l | grep -c "quant_strategies" || echo "0"
else
    echo "  ❌ Cron 任务安装失败"
    exit 1
fi
echo ""

# 显示配置摘要
echo "=========================================="
echo "  ✅ Cron 配置完成!"
echo "=========================================="
echo ""
echo "📅 已配置的任务:"
echo "  • 日线策略：每日 09:25, 13:00, 15:05"
echo "  • 中频交易：每 5 分钟 (交易时段)"
echo "  • 合并报告：每日 15:30"
echo "  • 状态检查：每周一 08:00"
echo "  • 日志清理：每周日 23:00"
echo ""
echo "📝 管理命令:"
echo "  查看任务：crontab -l"
echo "  编辑任务：crontab -e"
echo "  查看日志：tail -f logs/mf_sim.log"
echo "  备份任务：crontab -l > backup.txt"
echo ""
echo "📂 日志文件:"
echo "  日线策略：logs/bobquant.log"
echo "  中频交易：logs/mf_sim.log"
echo "  合并报告：logs/combined_report.log"
echo ""
echo "🎯 下次运行时间:"
echo "  周一 09:25 - 日线策略"
echo "  周一 09:30 - 中频交易 (开盘后)"
echo ""
echo "=========================================="
