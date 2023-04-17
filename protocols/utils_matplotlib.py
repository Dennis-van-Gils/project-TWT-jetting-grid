#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""utils_matplotlib.py

Utility functions for matplotlib.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "17-04-2023"
__version__ = "1.0"

from sys import platform
import matplotlib

if platform == "darwin":
    # OS X
    matplotlib.use("TkAgg")


def move_figure(f, x, y):
    """Move figure's upper left corner to pixel (x, y)"""
    backend = matplotlib.get_backend()
    if backend == "TkAgg":
        f.canvas.manager.window.wm_geometry(f"+{x}+{y}")
    elif backend == "WXAgg":
        f.canvas.manager.window.SetPosition((x, y))
    else:
        # This works for QT and GTK
        # You can also use window.setGeometry
        f.canvas.manager.window.move(x, y)
