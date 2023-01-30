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

# Constants taken from `src_mcu\src\constants.h`
# ----------------------------------------------
# The PCS spans (-7, -7) to (7, 7) where (0, 0) is the center of the grid.
# Physical valves are numbered 1 to 112, with 0 indicating 'no valve'.
PCS_X_MIN = -7  # Minimum x-axis coordinate of the PCS
PCS_X_MAX = 7  # Maximum x-axis coordinate of the PCS
NUMEL_PCS_AXIS = PCS_X_MAX - PCS_X_MIN + 1
N_VALVES = int(np.floor(NUMEL_PCS_AXIS * NUMEL_PCS_AXIS / 2))  # == 112

# Specific to this Python file
# ----------------------------
PCS_PIXEL_DIST = 64  # Pixel distance between the integer PCS coordinates

# OpenSimplex noise parameters
# ----------------------------
N_FRAMES = 200
N_PIXELS = PCS_PIXEL_DIST * (NUMEL_PCS_AXIS + 1)
TRANSPARENCY = 0.5

# Generate image stacks holding OpenSimplex noise
# -----------------------------------------------

cfg_A = stack_config(t_step=0.1, x_step=0.01, seed=1)
cfg_B = stack_config(t_step=0.1, x_step=0.005, seed=13)

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
del stack_B

rescale_stack(stack_A, symmetrically=False)

# Map into binary and calculate/tune transparency
if 1:
    stack_BW, alpha = binary_map_tune_transparency(
        stack_A, tuning_transp=TRANSPARENCY
    )
else:
    stack_BW, alpha = binary_map(stack_A)
del stack_A

# ------------------------------------------------------------------------------
#  PROTOCOL COORDINATE SYSTEM (PCS)
# ------------------------------------------------------------------------------
"""
  The jetting nozzles are laid out in a square grid, aka the protocol coordinate
  system (PCS).

  ●: Indicates a valve & nozzle
  -: Indicates no nozzle & valve exists

      -7 -6 -5 -4 -3 -2 -1  0  1  2  3  4  5  6  7
     ┌─────────────────────────────────────────────┐
   7 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
   6 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
   5 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
   4 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
   3 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
   2 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
   1 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
   0 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
  -1 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
  -2 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
  -3 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
  -4 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
  -5 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
  -6 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
  -7 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
     └─────────────────────────────────────────────┘
"""
# WORK IN PROGRESS

# Create a map holding the pixel locations inside the noise image corresponding
# to the valve locations. The index of below arrays does /not/ indicate the
# valve number as laid out in the lab, but instead is simply linearly going from
# left-to-right, repeating top-to-bottom.
_pxs = np.arange(
    PCS_PIXEL_DIST - 1, N_PIXELS - (PCS_PIXEL_DIST - 1), PCS_PIXEL_DIST
)
_grid_x, _grid_y = np.meshgrid(_pxs, _pxs)  # shape: (15, 15), (15, 15)
# `grid_x` and `grid_y` map /all/ integer PCS coordinates. We only need the
# locations that actually correspond to a valve.
valve_map_px_x = np.reshape(_grid_x, -1)[1::2]  # shape: (112,)
valve_map_px_y = np.reshape(_grid_y, -1)[1::2]  # shape: (112,)

# Create a stack holding the binary states of the valves
stack_valves = np.zeros([N_FRAMES, N_VALVES], dtype=bool)

# Create a stack to show only the opened valves for plotting purposes
valve_display_px_x = np.empty((N_FRAMES, N_VALVES))
valve_display_px_x[:] = np.nan
valve_display_px_y = np.empty((N_FRAMES, N_VALVES))
valve_display_px_y[:] = np.nan

for frame in range(N_FRAMES):
    stack_valves[frame, :] = (
        stack_BW[frame, valve_map_px_y, valve_map_px_x] == 0
    )

    for valve in range(N_VALVES):
        if stack_valves[frame, valve]:
            valve_display_px_x[frame, valve] = valve_map_px_x[valve]
            valve_display_px_y[frame, valve] = valve_map_px_y[valve]

# ------------------------------------------------------------------------------
#  Plot
# ------------------------------------------------------------------------------

fig_1 = plt.figure()
ax = plt.axes()
frame_text = ax.text(0, 1.02, "", transform=ax.transAxes)

# Plot the noise map
"""
hax_noise = ax.imshow(
    stack_BW[0],
    cmap="gray",
    vmin=0,
    vmax=1,
    interpolation="none",
)
"""

# Plot the valve locations
(hax_valves,) = ax.plot(
    valve_display_px_x[0, :],
    valve_display_px_y[0, :],
    marker="o",
    color="deeppink",
    linestyle="none",
    markersize=5,
)

ax.set_aspect("equal", adjustable="box")


def init_anim():
    frame_text.set_text("")
    # hax_noise.set_data(stack_BW[0])
    hax_valves.set_data(valve_display_px_x[0, :], valve_display_px_y[0, :])
    return hax_valves, frame_text


def anim(j):
    frame_text.set_text(f"frame {j:03d}, transparency = {alpha[j]:.2f}")
    # hax_noise.set_data(stack_BW[j])
    hax_valves.set_data(valve_display_px_x[j, :], valve_display_px_y[j, :])
    return hax_valves, frame_text


anim = animation.FuncAnimation(
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

# Export images to disk?
if 0:
    from PIL import Image

    def fig2data(fig):
        """
        @brief Convert a Matplotlib figure to a 4D numpy array with RGBA channels and return it
        @param fig a matplotlib figure
        @return a numpy 3D array of RGBA values
        """
        # draw the renderer
        fig.canvas.draw()

        # Get the RGBA buffer from the figure
        w, h = fig.canvas.get_width_height()
        buf = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8)
        buf.shape = (w, h, 4)

        # canvas.tostring_argb give pixmap in ARGB mode. Roll the ALPHA channel to have it in RGBA mode
        buf = np.roll(buf, 3, axis=2)
        return buf

    def fig2img(fig):
        """
        @brief Convert a Matplotlib figure to a PIL Image in RGBA format and return it
        @param fig a matplotlib figure
        @return a Python Imaging Library ( PIL ) image
        """
        # put the figure pixmap into a numpy array
        buf = fig2data(fig)
        w, h, d = buf.shape
        return Image.frombuffer("RGBA", (w, h), buf.tobytes())

    fig_1 = plt.figure(figsize=(10, 10))
    ax = plt.axes()
    ax.text(0, 1.02, "", transform=ax.transAxes)

    # Plot the noise map
    hax_noise = ax.imshow(
        stack_BW[0],
        cmap="gray",
        vmin=0,
        vmax=1,
        interpolation="none",
    )

    # Plot the valve locations
    (hax_valves,) = ax.plot(
        valve_display_px_x[0, :],
        valve_display_px_y[0, :],
        marker="o",
        color="deeppink",
        linestyle="none",
        markersize=5,
    )

    pil_imgs = []
    for j in range(N_FRAMES):
        frame_text.set_text(f"frame {j:03d}, transparency = {alpha[j]:.2f}")
        hax_noise.set_data(stack_BW[j])
        hax_valves.set_data(valve_display_px_x[j, :], valve_display_px_y[j, :])

        pil_img = fig2img(fig_1)
        pil_imgs.append(pil_img)

    pil_imgs[0].save(
        "output.gif",
        save_all=True,
        append_images=pil_imgs[1:],
        duration=40,
        loop=0,
    )

if 0:
    anim.save(
        "output.gif",
        dpi=120,
        writer="imagemagick",
        fps=20,
        progress_callback=lambda i, n: print(f"{i} of {N_FRAMES}"),
    )
