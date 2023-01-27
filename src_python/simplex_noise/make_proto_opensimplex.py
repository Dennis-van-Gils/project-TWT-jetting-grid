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
    add_stack_B_to_A,
    rescale_stack,
    binary_map,
    binary_map_tune_transparency,
)


# DEBUG info: Report on memory allocation?
REPORT_MALLOC = False
if REPORT_MALLOC:
    import tracemalloc
    from tracemalloc_report import tracemalloc_report

    tracemalloc.start()


class stack_config:
    def __init__(self, t_step, x_step, seed):
        self.t_step = t_step
        self.x_step = x_step
        self.seed = seed


# ------------------------------------------------------------------------------
#  Main
# ------------------------------------------------------------------------------

N_FRAMES = 200
N_PIXELS = 1000
TRANSPARENCY = 0.5

cfg_A = stack_config(t_step=0.1, x_step=0.01, seed=1)
cfg_B = stack_config(t_step=0.1, x_step=0.005, seed=13)

# Generate noise
stack_A = looping_animated_2D_image(
    N_frames=N_FRAMES,
    N_pixels_x=N_PIXELS,
    t_step=cfg_A.t_step,
    x_step=cfg_A.x_step,
    seed=cfg_A.seed,
    dtype=np.float32,
)

stack_B = looping_animated_2D_image(
    N_frames=N_FRAMES,
    N_pixels_x=N_PIXELS,
    t_step=cfg_B.t_step,
    x_step=cfg_B.x_step,
    seed=cfg_B.seed,
    dtype=np.float32,
)


add_stack_B_to_A(stack_A, stack_B)

rescale_stack(stack_A, symmetrically=False)

# Map into binary and calculate/tune transparency
if 1:
    stack_BW, alpha = binary_map_tune_transparency(
        stack_A, tuning_transp=TRANSPARENCY
    )
else:
    stack_BW, alpha = binary_map(stack_A)

# ------------------------------------------------------------------------------
#  Plot
# ------------------------------------------------------------------------------

fig_1 = plt.figure()
ax = plt.axes()
img = plt.imshow(
    stack_A[0],
    cmap="gray",
    vmin=0,
    vmax=1,
    interpolation="none",
)
frame_text = ax.text(0, 1.02, "", transform=ax.transAxes)


def init_anim():
    img.set_data(stack_A[0])
    frame_text.set_text("")
    return img, frame_text


def anim(j):
    img.set_data(stack_BW[j])
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
