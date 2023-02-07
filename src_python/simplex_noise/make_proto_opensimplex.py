#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Installation:
    conda create -n simplex python=3.10
    conda activate simplex
    pip install -r requirements.txt
    ipython make_proto_opensimplex.py
"""
__author__ = "Dennis van Gils"
# pylint: disable=invalid-name, missing-function-docstring, pointless-string-statement
# pylint: disable=unused-import

import sys
import os
from time import perf_counter

import numpy as np
from tqdm import trange
from numba import prange

from matplotlib import pyplot as plt
from matplotlib import animation
from matplotlib.ticker import MultipleLocator

from opensimplex_loops import looping_animated_2D_image
from utils_matplotlib import move_figure
from utils_pillow import fig2img_RGB
from utils_img_stack import (
    add_stack_B_to_A,
    rescale_stack,
    binarize_stack,
)
from utils_valves_stack import adjust_valve_times
import constants as C
import config_proto_OpenSimplex as CFG

# Global flags
PLOT_TO_SCREEN = 0  # [0] Save plots to disk, [1] Show on screen
SHOW_NOISE_IN_PLOT = 0  # [0] Only show valves,   [1] Show noise as well
SHOW_NOISE_AS_GRAY = 0  # Show noise as [0] BW,   [1] Grayscale

# ------------------------------------------------------------------------------
#  Calculate OpenSimplex noise
# ------------------------------------------------------------------------------

# Generate image stacks containing OpenSimplex noise. The images will have pixel
# values between [-1, 1].
img_stack_A = looping_animated_2D_image(
    N_frames=CFG.N_FRAMES,
    N_pixels_x=CFG.N_PIXELS,
    t_step=CFG.T_STEP_A,
    x_step=CFG.X_STEP_A,
    seed=CFG.SEED_A,
    dtype=np.float32,
)
print("")

if CFG.FEATURE_SIZE_B > 0:
    img_stack_B = looping_animated_2D_image(
        N_frames=CFG.N_FRAMES,
        N_pixels_x=CFG.N_PIXELS,
        t_step=CFG.T_STEP_B,
        x_step=CFG.X_STEP_B,
        seed=CFG.SEED_B,
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
    img_stack_A, CFG.BW_THRESHOLD, CFG.TUNE_TRANSPARENCY
)

# Determine which stack to plot
if SHOW_NOISE_AS_GRAY:
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
#  Determine the state of each valve
# ------------------------------------------------------------------------------

# Create a stack that will contain the boolean states of all valves
# NOTE: Use `int8` as type, not `bool` because we need number representation
# for later calculations.
valves_stack = np.zeros([CFG.N_FRAMES, C.N_VALVES], dtype=np.int8)

# Create a stack that will contain only the opened valves for plotting
valves_plot_pcs_x = np.empty((CFG.N_FRAMES, C.N_VALVES))
valves_plot_pcs_x[:] = np.nan
valves_plot_pcs_y = np.empty((CFG.N_FRAMES, C.N_VALVES))
valves_plot_pcs_y[:] = np.nan

# Populate stacks
for frame in prange(CFG.N_FRAMES):  # pylint: disable=not-an-iterable
    valves_stack[frame, :] = (
        img_stack_BW[frame, CFG.valve2px_y, CFG.valve2px_x] == 1
    )

    for valve in prange(C.N_VALVES):  # pylint: disable=not-an-iterable
        if valves_stack[frame, valve]:
            valves_plot_pcs_x[frame, valve] = C.valve2pcs_x[valve]
            valves_plot_pcs_y[frame, valve] = C.valve2pcs_y[valve]

# Calculate the valve transparency
alpha_valves = valves_stack.sum(1) / C.N_VALVES

print("Average transparencies:")
print(f"  alpha_noise  = {np.mean(alpha_noise):.2f}")
print(f"  alpha_valves = {np.mean(alpha_valves):.2f}\n")

# ------------------------------------------------------------------------------
#  Save `valves_stack` to disk
# ------------------------------------------------------------------------------

np.save(
    os.path.join(CFG.EXPORT_SUBFOLDER, "proto_example_valves_stack.npy"),
    valves_stack,
)
# sys.exit()

# Adjust valve times
valves_stack_out = adjust_valve_times(valves_stack, CFG.MIN_VALVE_DURATION)

np.save(
    os.path.join(
        CFG.EXPORT_SUBFOLDER, "proto_example_valves_stack_adjusted.npy"
    ),
    valves_stack_out,
)

# Calculate the valve transparency
alpha_valves_out = valves_stack_out.sum(1) / C.N_VALVES
print(f"  alpha_valves_out = {np.mean(alpha_valves_out):.2f}\n")

# Create a stack that will contain only the opened valves for plotting
valves_plot_pcs_x[:] = np.nan
valves_plot_pcs_y[:] = np.nan

# Populate stacks
for frame in prange(CFG.N_FRAMES):  # pylint: disable=not-an-iterable
    for valve in prange(C.N_VALVES):  # pylint: disable=not-an-iterable
        if valves_stack_out[frame, valve]:
            valves_plot_pcs_x[frame, valve] = C.valve2pcs_x[valve]
            valves_plot_pcs_y[frame, valve] = C.valve2pcs_y[valve]

# ------------------------------------------------------------------------------
#  Plot
# ------------------------------------------------------------------------------

fig_1 = plt.figure(figsize=(5, 5))
ax = plt.axes()
ax_text = ax.text(0, 1.02, "", transform=ax.transAxes)

# Plot the noise map
if SHOW_NOISE_IN_PLOT:
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
    if SHOW_NOISE_IN_PLOT:
        hax_noise.set_data(img_stack_plot[j])
    hax_valves.set_data(valves_plot_pcs_x[j, :], valves_plot_pcs_y[j, :])


fig_2 = plt.figure(2, figsize=(5, 4))
fig_2.set_tight_layout(True)
plt.plot(alpha_valves, "deeppink", label="valves original")
plt.plot(alpha_valves_out, "g", label="valves adjusted")
plt.plot(alpha_noise, "k", label="noise")
plt.xlim(0, CFG.N_FRAMES)
plt.title("transparency")
plt.xlabel("frame #")
plt.ylabel("alpha [0 - 1]")
plt.legend()

if PLOT_TO_SCREEN:
    # No export to disk
    anim = animation.FuncAnimation(
        fig_1,
        animate_fig_1,
        frames=CFG.N_FRAMES,
        interval=50,  # [ms] == 1000/FPS
        init_func=animate_fig_1(0),
    )

    move_figure(fig_1, 0, 0)
    move_figure(fig_2, 500, 0)

    plt.show(block=False)
    plt.pause(0.001)
    input("Press [Enter] to end.")
    plt.close("all")

else:
    # Export images to disk
    print("Generating gif frames...")
    tick = perf_counter()
    pil_imgs = []
    for frame in trange(CFG.N_FRAMES):
        animate_fig_1(frame)
        pil_img = fig2img_RGB(fig_1)
        pil_imgs.append(pil_img)
    print(f"done in {(perf_counter() - tick):.2f} s\n")

    print("Saving images...")
    tick = perf_counter()
    pil_imgs[0].save(
        os.path.join(CFG.EXPORT_SUBFOLDER, "proto_example.gif"),
        save_all=True,
        append_images=pil_imgs[1:],
        duration=50,  # [ms] == 1000/FPS
        loop=0,
    )
    fig_2.savefig(os.path.join(CFG.EXPORT_SUBFOLDER, "proto_example_alpha.png"))
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
