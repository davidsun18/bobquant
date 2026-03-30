#!/bin/bash
# ==========================================
# BOB 量化模拟盘 - 系统服务安装脚本
# 用于设置开机自启动（systemd）
# ==========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/bobquant-quant.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "=========================================="
echo "🔧 BOB 量化模拟盘 - 系统服务安装"
echo "=========================================="
echo ""

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用 sudo 运行此脚本"
    echo "   sudo ./install_service.sh"
    exit 1
fi

# 检查 systemd
if ! command -v systemctl &> /dev/null; then
    echo "❌ 未检测到 systemd，无法安装服务"
    echo ""
    echo "替代方案：将以下命令添加到 crontab:"
    echo "@reboot cd $SCRIPT_DIR && ./start_all.sh"
    exit 1
fi

echo "📄 复制服务文件到 $SYSTEMD_DIR..."
cp "$SERVICE_FILE" "$SYSTEMD_DIR/"

echo "🔄 重载 systemd 配置..."
systemctl daemon-reload

echo "✅ 服务安装成功!"
echo ""
echo "📋 管理命令:"
echo "   sudo systemctl start bobquant-quant     # 启动服务"
echo "   sudo systemctl stop bobquant-quant      # 停止服务"
echo "   sudo systemctl restart bobquant-quant   # 重启服务"
echo "   sudo systemctl enable bobquant-quant    # 启用开机自启动"
echo "   sudo systemctl disable bobquant-quant   # 禁用开机自启动"
echo "   sudo systemctl status bobquant-quant    # 查看状态"
echo "   journalctl -u bobquant-quant -f         # 查看日志"
echo ""

# 询问是否启用
read -p "是否现在启用开机自启动？(y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    systemctl enable bobquant-quant
    echo "✅ 已启用开机自启动"
    
    read -p "是否现在启动服务？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl start bobquant-quant
        sleep 2
        systemctl status bobquant-quant --no-pager
    fi
else
    echo "⏸️  跳过启用，可稍后手动运行: sudo systemctl enable bobquant-quant"
fi

echo ""
echo "=========================================="
echo "✅ 安装完成"
echo "=========================================="
