# BobQuant Windows 自动打包脚本
# 用法：.\build_windows.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BobQuant Windows 打包工具 v2.0" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查 Python
Write-Host "[1/7] 检查 Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ 错误：未找到 Python，请先安装 Python 3.10" -ForegroundColor Red
    Write-Host "  下载地址：https://www.python.org/downloads/release/python-31011/" -ForegroundColor Yellow
    exit 1
}

# 2. 安装依赖
Write-Host ""
Write-Host "[2/7] 安装依赖..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ 依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "  ⚠ 依赖安装警告，继续执行..." -ForegroundColor Yellow
}

# 3. 安装打包工具
Write-Host ""
Write-Host "[3/7] 安装 PyInstaller..." -ForegroundColor Yellow
pip install pyinstaller==5.7.0 --quiet
Write-Host "  ✓ PyInstaller 已安装" -ForegroundColor Green

# 4. 整理文件
Write-Host ""
Write-Host "[4/7] 整理项目文件..." -ForegroundColor Yellow
$BUILD_DIR = "build_windows"
if (Test-Path $BUILD_DIR) {
    Write-Host "  清理旧构建..." -ForegroundColor Gray
    Remove-Item $BUILD_DIR -Recurse -Force
}
New-Item -ItemType Directory -Path $BUILD_DIR | Out-Null
Write-Host "  ✓ 创建构建目录：$BUILD_DIR" -ForegroundColor Green

# 复制文件
$files = @(
    "bobquant",
    "bobquant_v2",
    "sim_trading",
    "web_ui.py",
    "auto_trade_v2.py",
    "requirements.txt",
    "start_all.bat",
    "README.md"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "  复制：$file" -ForegroundColor Gray
        Copy-Item -Path $file -Destination "$BUILD_DIR\" -Recurse -Force
    } else {
        Write-Host "  ⚠ 跳过 (不存在): $file" -ForegroundColor Yellow
    }
}

# 5. PyInstaller 打包
Write-Host ""
Write-Host "[5/7] PyInstaller 打包 Web UI..." -ForegroundColor Yellow
Set-Location $BUILD_DIR

$pyiArgs = @(
    "--onefile",
    "--windowed",
    "--name", "BobQuant",
    "--add-data", "bobquant;bobquant",
    "--add-data", "sim_trading;sim_trading",
    "--hidden-import", "pandas",
    "--hidden-import", "numpy",
    "--hidden-import", "baostock",
    "--hidden-import", "flask",
    "web_ui.py"
)

& pyinstaller @pyiArgs

if (Test-Path "dist\BobQuant.exe") {
    Write-Host "  ✓ Web UI 打包成功" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Web UI 打包失败，继续执行..." -ForegroundColor Yellow
}

Set-Location ..

# 6. 创建说明文档
Write-Host ""
Write-Host "[6/7] 创建说明文档..." -ForegroundColor Yellow
$readme = @"
# BobQuant 量化系统 - Windows 版

## 🚀 快速启动

### 方法 1: 直接运行 (推荐)
双击 `启动 BobQuant.bat`

### 方法 2: 命令行启动
1. 打开命令提示符 (cmd)
2. cd 到本目录
3. 运行：BobQuant.exe

## 📊 访问地址

启动后浏览器自动打开：http://localhost:5000

如果未自动打开，请手动访问:
- 本地：http://localhost:5000
- 局域网：http://[你的 IP]:5000

## 📁 文件说明

- `BobQuant.exe` - 主程序 (PyInstaller 打包)
- `启动 BobQuant.bat` - 一键启动脚本
- `bobquant/` - 策略引擎
- `sim_trading/` - 模拟盘数据
- `requirements.txt` - Python 依赖列表

## ⚠️ 注意事项

1. 首次启动会自动安装依赖 (约 2-5 分钟)
2. 需要保持网络连接 (获取股票数据)
3. 防火墙可能会提示允许访问，请选择"允许"

## 🔧 故障排查

### 问题 1: 双击没反应
解决：打开 `启动 BobQuant.bat` 查看错误信息

### 问题 2: 浏览器打不开
解决：手动访问 http://localhost:5000

### 问题 3: 数据不更新
解决：检查网络连接，重启程序

## 📞 技术支持

- 查看日志：sim_trading/logs/
- 问题反馈：[你的联系方式]

---

**版本**: 2.0
**日期**: $(Get-Date -Format "yyyy-MM-dd")
**系统**: Windows 10/11
"@

$readme | Out-File -FilePath "$BUILD_DIR\README.md" -Encoding UTF8
Write-Host "  ✓ 说明文档已创建" -ForegroundColor Green

# 7. 压缩
Write-Host ""
Write-Host "[7/7] 创建压缩包..." -ForegroundColor Yellow
$zipName = "BobQuant_Windows_v2.0_$(Get-Date -Format 'yyyyMMdd').zip"
Compress-Archive -Path "$BUILD_DIR\*" -DestinationPath $zipName -Force

if (Test-Path $zipName) {
    $size = (Get-Item $zipName).Length / 1MB
    Write-Host "  ✓ 打包完成：$zipName ($([math]::Round($size, 2)) MB)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ 压缩失败，请手动压缩 $BUILD_DIR 目录" -ForegroundColor Yellow
}

# 完成
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "打包完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "输出文件：$zipName" -ForegroundColor Cyan
Write-Host "文件大小：$([math]::Round((Get-Item $zipName).Length / 1MB, 2)) MB" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "1. 在 Windows 上测试安装包" -ForegroundColor White
Write-Host "2. 解压后运行 '启动 BobQuant.bat'" -ForegroundColor White
Write-Host "3. 浏览器访问 http://localhost:5000" -ForegroundColor White
Write-Host ""
