#!/bin/bash
# Data Bot 数据采集定时任务脚本
# 用于 crontab 定时执行

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="/home/openclaw/.openclaw/workspace"
LOG_DIR="${WORKSPACE_DIR}/logs"
LOG_FILE="${LOG_DIR}/data_collector_$(date +%Y-%m-%d).log"

# 确保日志目录存在
mkdir -p "${LOG_DIR}"

echo "========================================" >> "${LOG_FILE}"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始数据采集" >> "${LOG_FILE}"
echo "========================================" >> "${LOG_FILE}"

# 激活虚拟环境 (如果有)
# source /path/to/venv/bin/activate

# 执行数据采集
cd "${SCRIPT_DIR}"
python3 collect_data.py >> "${LOG_FILE}" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 数据采集成功" >> "${LOG_FILE}"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 数据采集失败 (exit code: ${EXIT_CODE})" >> "${LOG_FILE}"
fi

echo "" >> "${LOG_FILE}"

exit $EXIT_CODE
