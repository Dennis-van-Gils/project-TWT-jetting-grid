#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conda create -n simplex python=3.10
conda activate simplex
pip install -r requirements.txt
"""
# pylint: disable=invalid-name, missing-function-docstring, pointless-string-statement
# pylint: disable=unused-import

import os

import numpy as np
from numba import njit, prange

from matplotlib import pyplot as plt
from matplotlib import animation

from opensimplex_loops import looping_animated_2D_image
from utils import (
    move_figure,
    rescale,
    binary_map,
    binary_map_with_tuning,
    binary_map_with_tuning_newton,
)


# DEBUG info: Report on memory allocation?
REPORT_MALLOC = False
if REPORT_MALLOC:
    import tracemalloc
    from tracemalloc_report import tracemalloc_report

    tracemalloc.start()

# ------------------------------------------------------------------------------
#  Main
# ------------------------------------------------------------------------------

N_FRAMES = 200
N_PIXELS = 1000

# Generate noise
img_stack = looping_animated_2D_image(
    N_frames=N_FRAMES,
    N_pixels_x=N_PIXELS,
    t_step=0.1,
    x_step=0.01,
    seed=1,
    dtype=np.float32,
)

img_stack_2 = looping_animated_2D_image(
    N_frames=N_FRAMES,
    N_pixels_x=N_PIXELS,
    t_step=0.1,
    x_step=0.005,
    seed=13,
    dtype=np.float32,
)

# Add A & B into A
for i in prange(N_FRAMES):  # pylint: disable=not-an-iterable
    np.add(img_stack[i], img_stack_2[i], out=img_stack[i])

# Rescale noise
rescale(img_stack, symmetrically=False)

# Map into binary and calculate transparency
# img_stack_BW, alpha = binary_map(img_stack)
# img_stack_BW, alpha = binary_map_with_tuning(img_stack, tuning_transp=0.5)
img_stack_BW, alpha = binary_map_with_tuning_newton(
    img_stack, tuning_transp=0.5
)

# ------------------------------------------------------------------------------
#  Plot
# ------------------------------------------------------------------------------

fig_1 = plt.figure()
ax = plt.axes()
img = plt.imshow(
    img_stack[0],
    cmap="gray",
    vmin=0,
    vmax=1,
    interpolation="none",
)
frame_text = ax.text(0, 1.02, "", transform=ax.transAxes)


def init_anim():
    img.set_data(img_stack[0])
    frame_text.set_text("")
    return img, frame_text


def anim(j):
    img.set_data(img_stack_BW[j])
    frame_text.set_text(f"frame {j:03d}, transparency = {alpha[j]:.2f}")
    return img, frame_text


ani = animation.FuncAnimation(
    fig_1,
    anim,
    frames=N_FRAMES,
    interval=40,
    init_func=init_anim,  # blit=True,
)

# plt.grid(False)
# plt.axis("off")
move_figure(fig_1, 0, 0)

fig_2 = plt.figure(2)
plt.plot(alpha)
plt.xlim(0, N_FRAMES)
plt.title("transparency")
plt.xlabel("frame #")
plt.ylabel("alpha [0 - 1]")
move_figure(fig_2, 720, 0)

if REPORT_MALLOC:
    tracemalloc_report(tracemalloc.take_snapshot(), limit=4)

plt.show()
