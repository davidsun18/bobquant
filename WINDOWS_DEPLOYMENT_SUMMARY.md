# 🪟 Windows 部署总结

**目标**: 一键安装，开箱即用  
**创建时间**: 2026-03-28

---

## ✅ 已创建文件

| 文件 | 说明 | 位置 |
|------|------|------|
| `requirements.txt` | Python 依赖列表 | `quant_strategies/` |
| `start_all.bat` | Windows 启动脚本 | `quant_strategies/` |
| `build_windows.ps1` | 自动打包脚本 ⭐ | `quant_strategies/` |
| `WINDOWS_PACKAGE_GUIDE.md` | 详细打包指南 | `quant_strategies/` |
| `WINDOWS_DEPLOYMENT_SUMMARY.md` | 本文档 | `quant_strategies/` |

---

## 🎯 三种打包方案

### 方案 A: 便携版 (最简单⭐⭐⭐)

**大小**: ~150MB  
**难度**: ⭐

**步骤**:
```powershell
# 1. 复制整个项目到 Windows
# 2. 安装 Python 3.10
# 3. 双击 start_all.bat
# 4. 自动安装依赖并启动
```

**优点**:
- ✅ 最简单
- ✅ 无需打包
- ✅ 易于调试

**缺点**:
- ⚠️ 需要用户安装 Python
- ⚠️ 文件分散

---

### 方案 B: PyInstaller 打包 (推荐⭐⭐⭐)

**大小**: ~200MB  
**难度**: ⭐⭐

**步骤**:
```powershell
# 在 Windows 上执行
cd quant_strategies
.\build_windows.ps1

# 输出：BobQuant_Windows_v2.0_yyyyMMdd.zip
```

**优点**:
- ✅ 单个 exe 文件
- ✅ 无需 Python 环境
- ✅ 自动打包所有依赖

**缺点**:
- ⚠️ 文件较大
- ⚠️ 首次启动慢 (解压)

---

### 方案 C: Inno Setup 安装包 (专业⭐⭐⭐)

**大小**: ~180MB  
**难度**: ⭐⭐⭐

**步骤**:
1. PyInstaller 打包 exe
2. Inno Setup 制作安装包
3. 生成 setup.exe

**优点**:
- ✅ 专业安装界面
- ✅ 支持卸载
- ✅ 自动配置环境

**缺点**:
- ⚠️ 打包复杂
- ⚠️ 需要额外工具

---

## 🚀 快速开始 (推荐方案 B)

### 在 Windows 上操作:

```powershell
# 1. 准备环境
# 安装 Python 3.10: https://www.python.org/downloads/release/python-31011/
# 勾选 "Add Python to PATH"

# 2. 复制项目
# 将 quant_strategies 文件夹复制到 Windows

# 3. 执行打包脚本
cd quant_strategies
.\build_windows.ps1

# 4. 等待完成 (约 5-10 分钟)
# 输出：BobQuant_Windows_v2.0_yyyyMMdd.zip

# 5. 测试
# 解压 zip 文件
# 双击 "启动 BobQuant.bat"
# 浏览器打开 http://localhost:5000
```

---

## 📦 打包后文件结构

```
BobQuant_Windows_v2.0.zip (约 200MB)
├── BobQuant.exe          # 主程序 (PyInstaller 打包)
├── 启动 BobQuant.bat     # 一键启动脚本
├── README.md             # 使用说明
├── bobquant/             # 策略引擎
│   ├── main.py
│   ├── strategy/
│   └── config/
├── bobquant_v2/          # V2 策略
│   ├── strategy/
│   └── indicator/
└── sim_trading/          # 模拟盘
    ├── account_ideal.json
    └── 交易记录.json
```

---

## 💻 用户使用流程

### 安装:
1. 下载 `BobQuant_Windows_v2.0.zip`
2. 解压到任意目录 (如 `C:\BobQuant`)
3. 双击 `启动 BobQuant.bat`

### 使用:
1. 浏览器自动打开 http://localhost:5000
2. 查看持仓、盈亏
3. 自动交易 (周一 - 周五)

### 卸载:
1. 直接删除整个文件夹
2. 或使用 Inno Setup 卸载程序

---

## ⚠️ 注意事项

### 1. Python 版本
- **推荐**: Python 3.10
- **兼容**: 3.9, 3.11
- **不支持**: 3.8 及以下

### 2. 依赖包
某些包 Windows 需要特殊处理:
- **TA-Lib**: 需要预编译包
  - 下载：https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
  - 安装：`pip install TA_Lib‑0.4.25‑cp310‑cp310‑win_amd64.whl`

### 3. 防火墙
首次启动 Windows 防火墙会提示，需要:
- ✅ 允许 Python 访问网络
- ✅ 允许 5000 端口

### 4. 杀毒软件
可能会误报，需要:
- ✅ 添加信任/白名单
- ✅ 或暂时关闭

---

## 🔧 常见问题

### Q1: 打包后运行报错 "ModuleNotFoundError"
**解决**: 
```powershell
# 重新打包，添加 --hidden-import
pyinstaller --hidden-import pandas --hidden-import numpy web_ui.py
```

### Q2: 启动后浏览器空白
**解决**:
```powershell
# 检查端口是否被占用
netstat -ano | findstr :5000

# 如果占用，杀掉进程或换端口
```

### Q3: 自动交易不执行
**解决**:
```powershell
# 检查 Windows 任务计划程序
# 或手动执行
python auto_trade_v2.py
```

---

## 📊 打包时间估算

| 步骤 | 时间 |
|------|------|
| 安装依赖 | 2-5 分钟 |
| PyInstaller 打包 | 3-8 分钟 |
| 压缩 | 1-2 分钟 |
| **总计** | **6-15 分钟** |

---

## 🎯 下一步

### 立即执行:
1. ✅ 在 Windows 上测试便携版
2. ✅ 确认所有功能正常
3. ✅ 执行 `.\build_windows.ps1` 打包
4. ✅ 测试生成的 zip 文件

### 后续优化:
1. ⏳ 添加应用图标 (icon.ico)
2. ⏳ 制作 Inno Setup 安装包
3. ⏳ 添加自动更新功能
4. ⏳ 编写详细用户手册

---

## 📁 文件清单

### 核心文件:
- ✅ `web_ui.py` - Web 界面
- ✅ `auto_trade_v2.py` - 自动交易
- ✅ `bobquant/main.py` - 策略引擎
- ✅ `requirements.txt` - 依赖列表

### 打包工具:
- ✅ `build_windows.ps1` - 自动打包脚本
- ✅ `start_all.bat` - Windows 启动脚本

### 文档:
- ✅ `WINDOWS_PACKAGE_GUIDE.md` - 详细指南
- ✅ `WINDOWS_DEPLOYMENT_SUMMARY.md` - 总结
- ⏳ `README_Windows.md` - 用户手册 (待创建)

---

## ✅ 总结

**当前状态**:
- ✅ 依赖清单已创建
- ✅ 打包脚本已创建
- ✅ 启动脚本已创建
- ✅ 文档已创建

**需要测试**:
- ⏳ Windows 环境测试
- ⏳ PyInstaller 打包测试
- ⏳ 生成的 exe 功能测试

**推荐方案**: 先用便携版测试，确认正常后用 PyInstaller 打包

---

_文档创建：2026-03-28_  
_打包脚本：build_windows.ps1_  
_推荐方案：PyInstaller 一键打包_
