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
from time import perf_counter

import numpy as np
from tqdm import trange
from numba import prange

from matplotlib import pyplot as plt
from matplotlib import animation
from matplotlib.ticker import MultipleLocator

from utils_matplotlib import move_figure
from utils_pillow import fig2img_RGB
from utils_valves_stack import adjust_minimum_valve_durations, valve_on_off_PDFs
from utils_protocols import (
    generate_protocol_arrays_OpenSimplex,
    export_protocol_to_disk,
)

import constants as C
import config_proto_OpenSimplex as CFG

# Global flags
PLOT_TO_SCREEN = 1  # [0] Save plots to disk, [1] Show on screen
SHOW_NOISE_IN_PLOT = 1  # [0] Only show valves,   [1] Show noise as well
SHOW_NOISE_AS_GRAY = 0  # Show noise as [0] BW,   [1] Grayscale

# ------------------------------------------------------------------------------
#  Generate OpenSimplex protocol
# ------------------------------------------------------------------------------

# Flags usefull for developing. Leave both set to False for normal operation.
LOAD_FROM_CACHE = False
SAVE_TO_CACHE = True

if not LOAD_FROM_CACHE:
    # Normal operation
    (
        valves_stack,
        img_stack_noise,
        img_stack_noise_BW,
        alpha_noise,
        alpha_valves,
    ) = generate_protocol_arrays_OpenSimplex()

    if SAVE_TO_CACHE:
        print("Saving cache to disk...")
        tick = perf_counter()
        np.savez(
            "cache.npz",
            valves_stack=valves_stack,
            img_stack_noise=img_stack_noise,
            img_stack_noise_BW=img_stack_noise_BW,
            alpha_noise=alpha_noise,
            alpha_valves=alpha_valves,
        )
        print(f"done in {(perf_counter() - tick):.2f} s\n")

else:
    # Developer: Retrieving data straight from the cache file on disk
    print("Reading cache from disk...")
    tick = perf_counter()
    with np.load("cache.npz", allow_pickle=False) as cache:
        valves_stack = cache["valves_stack"]
        img_stack_noise = cache["img_stack_noise"]
        img_stack_noise_BW = cache["img_stack_noise_BW"]
        alpha_noise = cache["alpha_noise"]
        alpha_valves = cache["alpha_valves"]
    print(f"done in {(perf_counter() - tick):.2f} s\n")

# Determine which noise image stack to plot later
if SHOW_NOISE_AS_GRAY:
    img_stack_plot = img_stack_noise
else:
    img_stack_plot = img_stack_noise_BW
    del img_stack_noise  # Not needed anymore -> Free up large chunk of mem

# Adjust minimum valve durations
valves_stack_adj = adjust_minimum_valve_durations(
    valves_stack, CFG.MIN_VALVE_DURATION
)
alpha_valves_adjusted = valves_stack_adj.sum(1) / C.N_VALVES

# Export
export_protocol_to_disk(valves_stack, CFG.EXPORT_PATH_NO_EXT + ".txt")

# Report
print("Average transparencies:")
print(f"  alpha_noise           = {np.mean(alpha_noise):.2f}")
print(f"  alpha_valves          = {np.mean(alpha_valves):.2f}")
print(f"  alpha_valves_adjusted = {np.mean(alpha_valves_adjusted):.2f}\n")

# ------------------------------------------------------------------------------
#  Plot
# ------------------------------------------------------------------------------

fig_1 = plt.figure(figsize=(5, 5))
ax = plt.axes()
ax_text = ax.text(0, 1.02, "", transform=ax.transAxes)

# Plot the noise map
# ------------------

# Invert the colors. It is more intuitive to watch the turned on valves as black
# on a white background, than it is reversed. This is opposite to a masking
# layer in Photoshop, where a white region indicates True. Here, black indicates
# True.
img_stack_plot = 1 - img_stack_plot

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
# ------------------------

# Create a stack that will contain only the opened valves for plotting
valves_plot_pcs_x = np.empty((CFG.N_FRAMES, C.N_VALVES))
valves_plot_pcs_x[:] = np.nan
valves_plot_pcs_y = np.empty((CFG.N_FRAMES, C.N_VALVES))
valves_plot_pcs_y[:] = np.nan

# Populate stacks
for frame in prange(CFG.N_FRAMES):  # pylint: disable=not-an-iterable
    for valve in prange(C.N_VALVES):  # pylint: disable=not-an-iterable
        if valves_stack[frame, valve]:
            valves_plot_pcs_x[frame, valve] = C.valve2pcs_x[valve]
            valves_plot_pcs_y[frame, valve] = C.valve2pcs_y[valve]

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
plt.plot(alpha_valves_adjusted, "g", label="valves adjusted")
plt.plot(alpha_noise, "k", label="noise")
plt.xlim(0, CFG.N_FRAMES)
plt.title("transparency")
plt.xlabel("frame #")
plt.ylabel("alpha [0 - 1]")
plt.legend()

# Calculate PDFs
bins = np.arange(0, CFG.N_FRAMES)
pdf_off_1, pdf_on_1 = valve_on_off_PDFs(valves_stack, bins)
pdf_off_2, pdf_on_2 = valve_on_off_PDFs(valves_stack_adj, bins)

# Plot
fig_4, axs = plt.subplots(2)
fig_4.set_tight_layout(True)
move_figure(fig_4, 200, 0)

axs[0].set_title("valve OFF")
axs[0].step(bins[0:-1], pdf_off_1, "-r", where="mid", label="original")
axs[0].step(bins[0:-1], pdf_off_2, "-k", where="mid", label="adjusted")

axs[1].set_title("valve ON")
axs[1].step(bins[0:-1], pdf_on_1, "-r", where="mid", label="original")
axs[1].step(bins[0:-1], pdf_on_2, "-k", where="mid", label="adjusted")

for ax in axs:
    ax.set_xlabel("duration")
    ax.set_ylabel("PDF")
    ax.set_xlim(0, 60)
    ax.legend()
    ax.grid()

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
        CFG.EXPORT_PATH_NO_EXT + ".gif",
        save_all=True,
        append_images=pil_imgs[1:],
        duration=50,  # [ms] == 1000/FPS
        loop=0,
    )
    fig_2.savefig(CFG.EXPORT_PATH_NO_EXT + "_alpha.png")
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
