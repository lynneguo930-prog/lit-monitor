#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI 入口：GitHub Actions 统一执行 `python main.py`。

完整实现保留在单文件脚本 openalex_lit_monitor.py 中，本地也可直接运行该文件。
"""
import sys

from openalex_lit_monitor import main

if __name__ == "__main__":
    sys.exit(main())
