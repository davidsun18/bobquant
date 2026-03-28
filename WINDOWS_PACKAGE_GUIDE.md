# 🪟 Windows 打包部署方案

**目标**: 一键安装，开箱即用  
**格式**: EXE 安装包 (含所有依赖)  
**大小**: 约 200-300MB

---

## 📦 方案对比

### 方案 A: PyInstaller 打包 (推荐⭐⭐⭐)

**优点**:
- ✅ 单个 exe 文件
- ✅ 无需安装 Python
- ✅ 包含所有依赖
- ✅ 双击即可运行

**缺点**:
- ⚠️ 文件较大 (~200MB)
- ⚠️ 启动稍慢 (首次解压)
- ⚠️ 多进程支持复杂

**适用**: 最终用户分发

---

### 方案 B: 安装包 (Inno Setup) (推荐⭐⭐⭐)

**优点**:
- ✅ 专业安装界面
- ✅ 自动配置环境变量
- ✅ 可安装 Python+ 依赖
- ✅ 支持卸载

**缺点**:
- ⚠️ 需要用户安装
- ⚠️ 打包复杂

**适用**: 正式产品发布

---

### 方案 C: Docker Desktop (不推荐)

**优点**:
- ✅ 环境隔离
- ✅ 跨平台

**缺点**:
- ❌ Windows 需要 WSL2
- ❌ 用户学习成本高

**适用**: 开发环境

---

## 🎯 推荐方案：PyInstaller + Inno Setup

**两步打包**:
1. PyInstaller 打包 Python 为 exe
2. Inno Setup 制作安装包

---

## 📋 完整打包流程

### 第 1 步：准备 Windows 环境

**在 Windows 上操作** (或 Wine 环境):

```powershell
# 1. 安装 Python 3.10
# 下载地址：https://www.python.org/downloads/release/python-31011/
# 勾选 "Add Python to PATH"

# 2. 验证安装
python --version
pip --version

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装打包工具
pip install pyinstaller==5.7.0
pip install cx_Freeze==6.13.0
```

---

### 第 2 步：整理项目结构

```
bobquant_windows/
├── bobquant/                  # 主程序
│   ├── main.py
│   ├── strategy/
│   ├── data/
│   └── config/
├── bobquant_v2/              # V2 策略
│   ├── strategy/
│   └── indicator/
├── sim_trading/              # 模拟盘
│   ├── account_ideal.json
│   └── 交易记录.json
├── web/                      # Web UI
│   ├── templates/
│   └── static/
├── web_ui.py                 # Web 入口
├── auto_trade_v2.py          # 自动交易
├── start_all.bat             # Windows 启动脚本
├── requirements.txt          # 依赖列表
└── README.md                 # 使用说明
```

---

### 第 3 步：创建 PyInstaller 配置

**bobquant.spec**:
```python
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules

datas = []
datas += collect_data_files('baostock')
datas += collect_data_files('pandas')
datas += collect_data_files('numpy')

hiddenimports = []
hiddenimports += collect_submodules('baostock')
hiddenimports += collect_submodules('pandas')
hiddenimports += collect_submodules('numpy')

a = Analysis(
    ['web_ui.py', 'auto_trade_v2.py', 'bobquant/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BobQuant 量化系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # 图标
)
```

---

### 第 4 步：执行打包

```powershell
# 在 bobquant_windows 目录执行
pyinstaller --clean bobquant.spec

# 输出目录：dist/BobQuant 量化系统.exe
```

---

### 第 5 步：创建 Inno Setup 安装包

**bobquant.iss**:
```iss
[Setup]
AppName=BobQuant 量化交易系统
AppVersion=2.0
AppPublisher=BobQuant
DefaultDirName={autopf}\BobQuant
DefaultGroupName=BobQuant
LicenseFile=LICENSE
SetupIconFile=icon.ico
OutputDir=installer
OutputBaseFilename=BobQuant_Setup_2.0

[Files]
Source: "dist\*"; DestDir: "{app}"; Flags: recursesubdirs
Source: "bobquant\*"; DestDir: "{app}\bobquant"; Flags: recursesubdirs
Source: "sim_trading\*"; DestDir: "{app}\sim_trading"
Source: "requirements.txt"; DestDir: "{app}"
Source: "README.md"; DestDir: "{app}"

[Icons]
Name: "{group}\BobQuant Web UI"; Filename: "{app}\web_ui.exe"
Name: "{group}\BobQuant 自动交易"; Filename: "{app}\auto_trade_v2.exe"
Name: "{group}\查看持仓"; Filename: "{app}\sim_trading\account_ideal.json"
Name: "{group}\卸载 BobQuant"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\web_ui.exe"; Description: "启动 Web UI"; Flags: postinstall skipifsilent
```

---

### 第 6 步：编译安装包

```powershell
# 使用 Inno Setup Compiler
iscc bobquant.iss

# 输出：installer/BobQuant_Setup_2.0.exe
```

---

## 🚀 简化方案：便携版 (推荐先试这个)

**不需要打包，直接复制整个环境**:

### 在 Windows 上操作:

```powershell
# 1. 创建安装包目录
mkdir C:\BobQuant_Package
cd C:\BobQuant_Package

# 2. 安装 Python 到本地目录
# 下载 embeddable package: https://www.python.org/downloads/release/python-31011/
# 解压到 C:\BobQuant_Package\python

# 3. 配置 python310._pth
echo . > python310._pth
echo .\python310.zip >> python310._pth
echo .\DLLs >> python310._pth
echo .\Lib >> python310._pth
echo . >> python310._pth
echo import site >> python310._pth

# 4. 复制项目文件
xcopy /E /I /Y D:\workspace\quant_strategies\* .\

# 5. 创建启动脚本
echo @echo off > start.bat
echo echo 正在安装依赖... >> start.bat
echo python\python.exe -m pip install -r requirements.txt >> start.bat
echo echo 启动 Web UI... >> start.bat
echo start http://localhost:5000 >> start.bat
echo python\python.exe web_ui.py >> start.bat

# 6. 压缩
# 右键 -> 发送到 -> 压缩文件夹
# 重命名为：BobQuant_Portable_v2.0.zip
```

**用户使用方法**:
1. 解压 `BobQuant_Portable_v2.0.zip`
2. 双击 `start.bat`
3. 自动安装依赖并启动
4. 浏览器打开 http://localhost:5000

---

## 📦 自动化打包脚本

**build_windows.ps1** (PowerShell 脚本):

```powershell
# BobQuant Windows 打包脚本
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BobQuant Windows 打包工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. 检查 Python
Write-Host "`n[1/6] 检查 Python..." -ForegroundColor Yellow
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误：未找到 Python，请先安装 Python 3.10" -ForegroundColor Red
    exit 1
}

# 2. 安装依赖
Write-Host "`n[2/6] 安装依赖..." -ForegroundColor Yellow
pip install -r requirements.txt
pip install pyinstaller==5.7.0

# 3. 复制文件
Write-Host "`n[3/6] 整理文件..." -ForegroundColor Yellow
$BUILD_DIR = "build_windows"
if (Test-Path $BUILD_DIR) { Remove-Item $BUILD_DIR -Recurse -Force }
New-Item -ItemType Directory -Path $BUILD_DIR | Out-Null

Copy-Item -Path "bobquant" -Destination "$BUILD_DIR\bobquant" -Recurse
Copy-Item -Path "bobquant_v2" -Destination "$BUILD_DIR\bobquant_v2" -Recurse
Copy-Item -Path "sim_trading" -Destination "$BUILD_DIR\sim_trading" -Recurse
Copy-Item -Path "web_ui.py" -Destination "$BUILD_DIR\"
Copy-Item -Path "auto_trade_v2.py" -Destination "$BUILD_DIR\"
Copy-Item -Path "requirements.txt" -Destination "$BUILD_DIR\"

# 4. PyInstaller 打包
Write-Host "`n[4/6] PyInstaller 打包..." -ForegroundColor Yellow
Set-Location $BUILD_DIR
pyinstaller --onefile --windowed --name BobQuant web_ui.py
Set-Location ..

# 5. 创建启动脚本
Write-Host "`n[5/6] 创建启动脚本..." -ForegroundColor Yellow
@"
@echo off
echo ========================================
echo BobQuant 量化系统
echo ========================================
echo.
echo 正在启动 Web UI...
echo 浏览器访问：http://localhost:5000
echo.
start http://localhost:5000
BobQuant.exe
pause
"@ | Out-File -FilePath "$BUILD_DIR\启动 BobQuant.bat" -Encoding ASCII

# 6. 压缩
Write-Host "`n[6/6] 创建压缩包..." -ForegroundColor Yellow
Compress-Archive -Path "$BUILD_DIR\*" -DestinationPath "BobQuant_Windows_v2.0.zip" -Force

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "打包完成！" -ForegroundColor Green
Write-Host "文件：BobQuant_Windows_v2.0.zip" -ForegroundColor Green
Write-Host "大小：$(Get-Item "BobQuant_Windows_v2.0.zip" | Select-Object -ExpandProperty Length / 1MB) MB" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
```

---

## 🎯 最简单方案：使用现有工具

### 方案 1: Auto-EXE (最快)

使用 **auto-py-to-exe** (图形界面):

```powershell
# 1. 安装
pip install auto-py-to-exe

# 2. 启动
auto-py-to-exe

# 3. 图形界面操作:
#    - 选择 web_ui.py
#    - 选择 "One File"
#    - 添加 icon.ico
#    - 点击 "Convert"
```

### 方案 2: Nuitka (性能更好)

```powershell
# 1. 安装
pip install nuitka

# 2. 打包
python -m nuitka --onefile --windows-disable-console web_ui.py

# 输出：web_ui.exe
```

---

## 📊 方案对比总结

| 方案 | 难度 | 文件大小 | 启动速度 | 推荐度 |
|------|------|---------|---------|--------|
| **便携版** | ⭐ | 150MB | 快 | ⭐⭐⭐ |
| **PyInstaller** | ⭐⭐ | 200MB | 中 | ⭐⭐⭐ |
| **Inno Setup** | ⭐⭐⭐ | 180MB | 快 | ⭐⭐⭐ |
| **auto-py-to-exe** | ⭐ | 200MB | 中 | ⭐⭐ |
| **Nuitka** | ⭐⭐ | 150MB | 快 | ⭐⭐⭐⭐ |

---

## 🎯 我的建议

### 先用便携版测试 (最简单):
```powershell
# 1. 复制整个项目到 Windows
# 2. 安装 Python 3.10
# 3. 运行：pip install -r requirements.txt
# 4. 运行：python web_ui.py
```

### 确认能用后打包:
```powershell
# 使用 build_windows.ps1 一键打包
.\build_windows.ps1
```

### 最终发布:
```
BobQuant_Windows_v2.0.zip (约 200MB)
├── BobQuant.exe          # 主程序
├── 启动 BobQuant.bat     # 启动脚本
├── bobquant/             # 策略引擎
├── sim_trading/          # 模拟盘数据
└── README.md             # 使用说明
```

---

## 📁 需要创建的文件

我已经创建了:
- ✅ `requirements.txt` - 依赖列表
- ✅ `WINDOWS_PACKAGE_GUIDE.md` - 本文档

还需要创建:
- ⏳ `bobquant.spec` - PyInstaller 配置
- ⏳ `bobquant.iss` - Inno Setup 配置
- ⏳ `build_windows.ps1` - 自动打包脚本
- ⏳ `start_all.bat` - Windows 启动脚本
- ⏳ `icon.ico` - 应用图标

---

需要我帮你创建这些文件吗？或者你想先试试便携版方案？
