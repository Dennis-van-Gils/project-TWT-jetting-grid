#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Installation:
    conda create -n simplex python=3.10
    conda activate simplex
    pip install -r requirements.txt
    ipython make_proto_opensimplex.py
"""
# pylint: disable=invalid-name, missing-function-docstring, pointless-string-statement
# pylint: disable=unused-import

import sys
from time import perf_counter

import numpy as np
from tqdm import trange
from numba import prange

from matplotlib import pyplot as plt
from matplotlib import animation
from matplotlib.ticker import MultipleLocator

plt.rcParams["figure.figsize"] = [5, 4]

from opensimplex_loops import looping_animated_2D_image
from utils import (
    move_figure,
    add_stack_B_to_A,
    rescale_stack,
    binarize_stack,
)
from utils_pillow import fig2img_RGB
import constants as C

# DEBUG info: Report on memory allocation?
REPORT_MALLOC = False
if REPORT_MALLOC:
    import tracemalloc
    from tracemalloc_report import tracemalloc_report

    tracemalloc.start()

# ------------------------------------------------------------------------------
#  ProtoConfig
# ------------------------------------------------------------------------------


class ProtoConfig:
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
        self.x_step = np.divide(1, feature_size * C.PCS_PIXEL_DIST / 32)
        np.seterr(divide="warn")


# ------------------------------------------------------------------------------
#  Calculate OpenSimplex noise
# ------------------------------------------------------------------------------

cfg_A = ProtoConfig(
    C.N_FRAMES, C.N_PIXELS, C.T_STEP_A, C.FEATURE_SIZE_A, C.SEED_A
)
cfg_B = ProtoConfig(
    C.N_FRAMES, C.N_PIXELS, C.T_STEP_B, C.FEATURE_SIZE_B, C.SEED_B
)

# Generate image stacks containing OpenSimplex noise. The images will have pixel
# values between [-1, 1].
img_stack_A = looping_animated_2D_image(
    N_frames=cfg_A.N_frames,
    N_pixels_x=cfg_A.N_pixels,
    t_step=cfg_A.t_step,
    x_step=cfg_A.x_step,
    seed=cfg_A.seed,
    dtype=np.float32,
)
print("")

if C.FEATURE_SIZE_B > 0:
    img_stack_B = looping_animated_2D_image(
        N_frames=cfg_B.N_frames,
        N_pixels_x=cfg_B.N_pixels,
        t_step=cfg_B.t_step,
        x_step=cfg_B.x_step,
        seed=cfg_B.seed,
        dtype=np.float32,
    )
    print("")

    add_stack_B_to_A(img_stack_A, img_stack_B)  # Pixel vals now between [-2, 2]
    del img_stack_B

# Rescale and offset all images in the stack to lie within the range [0, 1].
# Leave `symmetrically=True` to prevent biasing the pixel intensity distribution
# towards 0 or 1.
rescale_stack(img_stack_A, symmetrically=True)

# Transform grayscale noise into binary BW map and calculate/tune transparency
img_stack_BW, alpha_noise = binarize_stack(
    img_stack_A, C.BW_THRESHOLD, C.TUNE_TRANSPARENCY
)

# Determine which stack to plot
if C.SHOW_NOISE_AS_GRAY:
    img_stack_plot = img_stack_A
else:
    img_stack_plot = img_stack_BW
    del img_stack_A

# Invert the colors. It is more intuitive to watch the turned on valves as black
# on a white background, than it is reversed. This is opposite to a masking
# layer in Photoshop, where a white region indicates True. Here, black indicates
# True.
img_stack_plot = 1 - img_stack_plot

# ------------------------------------------------------------------------------
#  Valve transformations
# ------------------------------------------------------------------------------
# NOTE: The valve index of below arrays does /not/ indicate the valve number as
# laid out in the lab, but instead is simply linearly increasing.

# Create a map holding the pixel locations inside the noise image corresponding
# to each valve location
_pxs = np.arange(
    C.PCS_PIXEL_DIST - 1, C.N_PIXELS - (C.PCS_PIXEL_DIST - 1), C.PCS_PIXEL_DIST
)
_grid_x, _grid_y = np.meshgrid(_pxs, _pxs)  # shape: (15, 15), (15, 15)
# `grid_x` and `grid_y` map /all/ integer PCS coordinates. We only need the
# locations that actually correspond to a valve.
valve2px_x = np.reshape(_grid_x, -1)[1::2]  # shape: (112,)
valve2px_y = np.reshape(_grid_y, -1)[1::2]  # shape: (112,)

# Create a map holding the PCS coordinates of each valve
_coords = np.arange(C.PCS_X_MIN, C.PCS_X_MAX + 1)
_grid_x, _grid_y = np.meshgrid(_coords, _coords)  # shape: (15, 15), (15, 15)
# `grid_x` and `grid_y` map /all/ integer PCS coordinates. We only need the
# locations that actually correspond to a valve.
valve2pcs_x = np.reshape(_grid_x, -1)[1::2]  # shape: (112,)
valve2pcs_y = np.reshape(_grid_y, -1)[1::2]  # shape: (112,)

# ------------------------------------------------------------------------------
#  Determine the state of each valve
# ------------------------------------------------------------------------------

# Create a stack holding the boolean states of all valves
valves_stack = np.zeros([C.N_FRAMES, C.N_VALVES], dtype=bool)

# Create a stack for plotting only the opened valves
valves_plot_pcs_x = np.empty((C.N_FRAMES, C.N_VALVES))
valves_plot_pcs_x[:] = np.nan
valves_plot_pcs_y = np.empty((C.N_FRAMES, C.N_VALVES))
valves_plot_pcs_y[:] = np.nan

# Populate stacks
for frame in prange(C.N_FRAMES):  # pylint: disable=not-an-iterable
    valves_stack[frame, :] = img_stack_BW[frame, valve2px_y, valve2px_x] == 1

    for valve in prange(C.N_VALVES):  # pylint: disable=not-an-iterable
        if valves_stack[frame, valve]:
            valves_plot_pcs_x[frame, valve] = valve2pcs_x[valve]
            valves_plot_pcs_y[frame, valve] = valve2pcs_y[valve]

# Calculate the valve transparency
alpha_valves = valves_stack.sum(1) / C.N_VALVES

print("Average transparencies:")
print(f"  alpha_noise  = {np.mean(alpha_noise):.2f}")
print(f"  alpha_valves = {np.mean(alpha_valves):.2f}\n")

if REPORT_MALLOC:
    tracemalloc_report(tracemalloc.take_snapshot(), limit=4)

# ------------------------------------------------------------------------------
#  Save `valves_stack` to disk
# ------------------------------------------------------------------------------

np.save("proto_valves_stack.npy", valves_stack)
# sys.exit()

# ------------------------------------------------------------------------------
#  Plot
# ------------------------------------------------------------------------------

fig_1 = plt.figure(figsize=(5, 5))
ax = plt.axes()
ax_text = ax.text(0, 1.02, "", transform=ax.transAxes)

# Plot the noise map
if C.SHOW_NOISE_IN_PLOT:
    hax_noise = ax.imshow(
        img_stack_plot[0],
        cmap="gray",
        vmin=0,
        vmax=1,
        interpolation="none",
        origin="lower",
        extent=[
            C.PCS_X_MIN - 1,
            C.PCS_X_MAX + 1,
            C.PCS_X_MIN - 1,
            C.PCS_X_MAX + 1,
        ],
    )

# Plot the valve locations
(hax_valves,) = ax.plot(
    valves_plot_pcs_x[0, :],
    valves_plot_pcs_y[0, :],
    marker="o",
    color="deeppink",
    linestyle="none",
    markersize=5,
)

# major_locator = MultipleLocator(1)
# ax.xaxis.set_major_locator(major_locator) # Slows down drawing a lot!
# ax.yaxis.set_major_locator(major_locator) # Slows down drawing a lot!
ax.set_aspect("equal", adjustable="box")
ax.set_xlim(C.PCS_X_MIN - 1, C.PCS_X_MAX + 1)
ax.set_ylim(C.PCS_X_MIN - 1, C.PCS_X_MAX + 1)
ax.grid(which="major")
# ax.axis("off")


def animate_fig_1(j):
    ax_text.set_text(f"frame {j:04d}")
    if C.SHOW_NOISE_IN_PLOT:
        hax_noise.set_data(img_stack_plot[j])
    hax_valves.set_data(valves_plot_pcs_x[j, :], valves_plot_pcs_y[j, :])


fig_2 = plt.figure(2)
fig_2.set_tight_layout(True)
plt.plot(alpha_valves, "deeppink", label="valves")
plt.plot(alpha_noise, "k", label="noise")
plt.xlim(0, C.N_FRAMES)
plt.title("transparency")
plt.xlabel("frame #")
plt.ylabel("alpha [0 - 1]")
plt.legend()

fig_3 = plt.figure(3)
fig_3.set_tight_layout(True)
plt.plot(valves_stack[:, 0])
plt.xlim(0, C.N_FRAMES)
plt.title("valve 0")
plt.xlabel("frame #")
plt.ylabel("state [0 - 1]")

if C.PLOT_TO_SCREEN:
    # No export to disk
    anim = animation.FuncAnimation(
        fig_1,
        animate_fig_1,
        frames=C.N_FRAMES,
        interval=50,  # [ms] == 1000/FPS
        init_func=animate_fig_1(0),
    )

    move_figure(fig_1, 0, 0)
    move_figure(fig_2, 500, 0)
    move_figure(fig_3, 500 + 500, 0)

    plt.show(block=False)
    plt.pause(0.001)
    input("Press [Enter] to end.")
    plt.close("all")

else:
    # Export images to disk
    print("Generating gif frames...")
    tick = perf_counter()
    pil_imgs = []
    for frame in trange(C.N_FRAMES):
        animate_fig_1(frame)
        pil_img = fig2img_RGB(fig_1)
        pil_imgs.append(pil_img)
    print(f"done in {(perf_counter() - tick):.2f} s\n")

    print("Saving images...")
    tick = perf_counter()
    pil_imgs[0].save(
        "proto_anim.gif",
        save_all=True,
        append_images=pil_imgs[1:],
        duration=50,  # [ms] == 1000/FPS
        loop=0,
    )
    fig_2.savefig("proto_alpha.png")
    print(f"done in {(perf_counter() - tick):.2f} s\n")

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
