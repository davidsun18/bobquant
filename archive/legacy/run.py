#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BobQuant 启动入口"""
import sys
from pathlib import Path

# 确保项目根目录在 sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from bobquant.main import main_loop

if __name__ == '__main__':
    main_loop()
