#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conda create -n simplex python=3.10
conda activate simplex
pip install -r requirements.txt
ipython make_proto_opensimplex.py
"""
# pylint: disable=invalid-name, missing-function-docstring, pointless-string-statement
# pylint: disable=unused-import

from time import perf_counter

import numpy as np
from tqdm import trange

from matplotlib import pyplot as plt
from matplotlib import animation

from opensimplex_loops import looping_animated_2D_image
from utils import (
    move_figure,
    add_stack_B_to_A,
    rescale_stack,
    binarize_stack,
)
from utils_pillow import fig2img_RGB, fig2img_RGBA


# DEBUG info: Report on memory allocation?
REPORT_MALLOC = False
if REPORT_MALLOC:
    import tracemalloc
    from tracemalloc_report import tracemalloc_report

    tracemalloc.start()

# ------------------------------------------------------------------------------
#  proto_config
# ------------------------------------------------------------------------------


class proto_config:
    def __init__(
        self,
        N_frames: int,
        N_pixels: int,
        t_step: float,
        feature_size: int,
        seed: int,
    ):
        self.N_frames = N_frames
        self.N_pixels = N_pixels
        self.t_step = t_step
        self.feature_size = feature_size
        self.seed = seed

        # Derived
        np.seterr(divide="ignore")
        self.x_step = np.divide(1, feature_size)
        np.seterr(divide="warn")


# ------------------------------------------------------------------------------
#  Main
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

# Constants taken from `src_mcu\src\constants.h`
# ----------------------------------------------
# The PCS spans (-7, -7) to (7, 7) where (0, 0) is the center of the grid.
# Physical valves are numbered 1 to 112, with 0 indicating 'no valve'.
PCS_X_MIN = -7  # Minimum x-axis coordinate of the PCS
PCS_X_MAX = 7  # Maximum x-axis coordinate of the PCS
NUMEL_PCS_AXIS = PCS_X_MAX - PCS_X_MIN + 1
N_VALVES = int(np.floor(NUMEL_PCS_AXIS * NUMEL_PCS_AXIS / 2))  # == 112


# General constants
# -----------------
PCS_PIXEL_DIST = 32  # 32, Pixel distance between the integer PCS coordinates

PLOT_NOISE = True
PLOT_NOISE_AS_GRAY = False  # True: grayscale, False: B&W

# Protocol parameters
# -------------------
N_FRAMES = 2000
N_PIXELS = PCS_PIXEL_DIST * (NUMEL_PCS_AXIS + 1)

# [0-1] Threshold level to convert grayscale noise to binary BW map.
BW_THRESHOLD = 0.5

# Interpret `BW_THRESHOLD` instead as a wanted transparency to solve for?
TUNE_TRANSPARENCY = True

T_STEP_A = 0.1
T_STEP_B = 0.1

FEATURE_SIZE_A = 50  # 50
FEATURE_SIZE_B = 100  # 100, 0 indicates to not use stack B

SEED_A = 1
SEED_B = 13


# Generate image stacks holding OpenSimplex noise
# -----------------------------------------------
cfg_A = proto_config(N_FRAMES, N_PIXELS, T_STEP_A, FEATURE_SIZE_A, SEED_A)
cfg_B = proto_config(N_FRAMES, N_PIXELS, T_STEP_B, FEATURE_SIZE_B, SEED_B)

stack_A = looping_animated_2D_image(
    N_frames=cfg_A.N_frames,
    N_pixels_x=cfg_A.N_pixels,
    t_step=cfg_A.t_step,
    x_step=cfg_A.x_step,
    seed=cfg_A.seed,
    dtype=np.float32,
)
print("")

if FEATURE_SIZE_B > 0:
    stack_B = looping_animated_2D_image(
        N_frames=cfg_B.N_frames,
        N_pixels_x=cfg_B.N_pixels,
        t_step=cfg_B.t_step,
        x_step=cfg_B.x_step,
        seed=cfg_B.seed,
        dtype=np.float32,
    )
    print("")

    add_stack_B_to_A(stack_A, stack_B)
    del stack_B

rescale_stack(stack_A, symmetrically=False)

# Transform grayscale noise into binary BW map and calculate/tune transparency
stack_BW, alpha = binarize_stack(stack_A, BW_THRESHOLD, TUNE_TRANSPARENCY)

# Determine which stack to plot
if PLOT_NOISE_AS_GRAY:
    stack_to_plot = stack_A
else:
    stack_to_plot = stack_BW
    del stack_A

# Invert the colors. It is more intuitive to watch the turned on valves as black
# on a white background, than it is reversed. This is opposite to a masking
# layer in Photoshop, where a white region indicates True. Here, black indicates
# True.
stack_to_plot = 1 - stack_to_plot

# ------------------------------------------------------------------------------
#  PROTOCOL COORDINATE SYSTEM (PCS)
# ------------------------------------------------------------------------------

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

# Populate stacks
for frame in range(N_FRAMES):
    stack_valves[frame, :] = (
        stack_BW[frame, valve_map_px_y, valve_map_px_x] == 1
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
if PLOT_NOISE:
    hax_noise = ax.imshow(
        stack_to_plot[0],
        cmap="gray",
        vmin=0,
        vmax=1,
        interpolation="none",
        origin="lower",
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

ax.set_aspect("equal", adjustable="box")
ax.set_xlim(0, N_PIXELS)
ax.set_ylim(0, N_PIXELS)


def init_anim():
    frame_text.set_text("")
    if PLOT_NOISE:
        hax_noise.set_data(stack_to_plot[0])
    hax_valves.set_data(valve_display_px_x[0, :], valve_display_px_y[0, :])
    return hax_valves, frame_text


def anim(j):
    frame_text.set_text(f"frame {j:03d}, transparency = {alpha[j]:.2f}")
    if PLOT_NOISE:
        hax_noise.set_data(stack_to_plot[j])
    hax_valves.set_data(valve_display_px_x[j, :], valve_display_px_y[j, :])
    return hax_valves, frame_text


anim = animation.FuncAnimation(
    fig_1,
    anim,
    frames=N_FRAMES,
    interval=50,  # [ms] == 1000/FPS
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

# plt.show()

# Export images to disk?
if 1:
    fig_1 = plt.figure(figsize=(5, 5))  # figsize * 100 = pixels
    ax = plt.axes()
    frame_text = ax.text(0, 1.02, "", transform=ax.transAxes)

    # Plot the noise map
    if PLOT_NOISE:
        hax_noise = ax.imshow(
            stack_to_plot[0],
            cmap="gray",
            vmin=0,
            vmax=1,
            interpolation="none",
            origin="lower",
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

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(0, N_PIXELS)
    ax.set_ylim(0, N_PIXELS)

    print("Generating gif frames...")
    tick = perf_counter()
    pil_imgs = []

    for j in trange(N_FRAMES):
        frame_text.set_text(f"frame {j:03d}")
        if PLOT_NOISE:
            hax_noise.set_data(stack_to_plot[j])
        hax_valves.set_data(valve_display_px_x[j, :], valve_display_px_y[j, :])

        pil_img = fig2img_RGB(fig_1)
        pil_imgs.append(pil_img)

    print(f"done in {(perf_counter() - tick):.2f} s\n")

    pil_imgs[0].save(
        "output.gif",
        save_all=True,
        append_images=pil_imgs[1:],
        duration=50,  # [ms] == 1000/FPS
        loop=0,
    )

"""
    # NOTE: Don't use below image export mechanism. It is extremely memory
    # hungry & slow.

    anim.save(
        "output.gif",
        dpi=120,
        writer="imagemagick",
        fps=20,
        progress_callback=lambda i, n: print(f"{i + 1} of {N_FRAMES}"),
    )
"""
