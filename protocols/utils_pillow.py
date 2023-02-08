#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utility functions for PIL "pillow": Fork of the Python Imaging Library
"""
__author__ = "Dennis van Gils"
# pylint: disable=invalid-name

import io

import numpy as np
from matplotlib.figure import Figure
from PIL import Image


def fig2data_RGB(fig: Figure) -> np.ndarray:
    """Convert a Matplotlib figure to a 3D numpy array with RGB channels and
    return it.

    Returns:
        A numpy 3D array of RGB values
    """
    # Draw the renderer
    fig.canvas.draw()

    # Get the RGBA buffer from the figure
    w, h = fig.canvas.get_width_height()
    buf = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    buf.shape = (w, h, 3)
    return buf


def fig2img_RGB(fig: Figure) -> Image.Image:
    """Convert a Matplotlib figure to a PIL Image in RGB format and return it.

    Returns:
        A Python Imaging Library (PIL) image
    """
    buf = fig2data_RGB(fig)
    w, h, _d = buf.shape
    return Image.frombuffer("RGB", (w, h), buf.tobytes())


def fig2data_RGBA(fig: Figure) -> np.ndarray:
    """Convert a Matplotlib figure to a 4D numpy array with RGBA channels and
    return it.

    Returns:
        A numpy 3D array of RGBA values
    """
    # Draw the renderer
    fig.canvas.draw()

    # Get the ARGB buffer from the figure
    w, h = fig.canvas.get_width_height()
    buf = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8)
    buf.shape = (w, h, 4)

    # Roll the ALPHA channel to have it in RGBA mode
    buf = np.roll(buf, 3, axis=2)
    return buf


def fig2img_RGBA(fig: Figure) -> Image.Image:
    """Convert a Matplotlib figure to a PIL Image in RGBA format and return it.

    Returns:
        A Python Imaging Library (PIL) image
    """
    buf = fig2data_RGBA(fig)
    w, h, _d = buf.shape
    return Image.frombuffer("RGBA", (w, h), buf.tobytes())


def fig2img_alt(fig: Figure) -> Image.Image:
    """Convert a Matplotlib figure to a PIL Image in RGBA format and return it.

    NOTE: Timed to be twice as slow as `fig2img()` on my work laptop.

    Returns:
        A Python Imaging Library (PIL) image
    """
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format="png")
    im = Image.open(img_buf)
    return im
