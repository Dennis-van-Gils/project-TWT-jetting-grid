#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Installation:
    In Anaconda prompt:
    > conda create -n twt python=3.10
    > conda activate twt
    > pip install -r requirements.txt

Usage:
    Edit `config_proto_opensimplex.py` to your needs.
    Set global flags in this file to your needs.
    In Anaconda prompt:
    > conda activate twt
    > ipython make_proto_opensimplex.py
"""
__author__ = "Dennis van Gils"
# pylint: disable=invalid-name, missing-function-docstring

from time import perf_counter

import numpy as np
from tqdm import trange

from matplotlib import pyplot as plt
from matplotlib import animation

from utils_matplotlib import move_figure
from utils_pillow import fig2img_RGB
from utils_valves_stack import (
    adjust_minimum_valve_durations,
    valve_on_off_PDFs,
)
from utils_protocols import (
    generate_protocol_arrays_OpenSimplex,
    export_protocol_to_disk,
)

import constants as C
import config_proto_opensimplex as CFG

# Global flags
EXPORT_GIF = 0  # Export animation as a .gif to disk?
SHOW_NOISE_IN_PLOT = 1  # [0] Only show valves,   [1] Show noise as well
SHOW_NOISE_AS_GRAY = 0  # Show noise as [0] BW,   [1] Grayscale

# ------------------------------------------------------------------------------
#  Generate OpenSimplex protocol
# ------------------------------------------------------------------------------

# Flags useful for developing. Leave both set to False for normal operation.
LOAD_FROM_CACHE = False
SAVE_TO_CACHE = False

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
(
    valves_stack_adj,
    alpha_valves_adj,
) = adjust_minimum_valve_durations(valves_stack, CFG.MIN_VALVE_DURATION)

# Calculate PDFs
bins, pdf_off, pdf_on = valve_on_off_PDFs(valves_stack, CFG.DT_FRAME)
_, pdf_off_adj, pdf_on_adj = valve_on_off_PDFs(valves_stack_adj, CFG.DT_FRAME)

# Report transparencies
def build_stats_str(x):
    return f"{np.mean(x):.2f} ± {np.std(x):.3f}"


stats_alpha_noise = build_stats_str(alpha_noise)
stats_alpha_valves = build_stats_str(alpha_valves)
stats_alpha_valves_adj = build_stats_str(alpha_valves_adj)
print("Transparencies (avg ± stdev):")
print(f"  alpha_noise      = {stats_alpha_noise}")
print(f"  alpha_valves     = {stats_alpha_valves}")
print(f"  alpha_valves_adj = {stats_alpha_valves_adj}\n")

# ------------------------------------------------------------------------------
#  Export protocol to disk
# ------------------------------------------------------------------------------

# Protocol formatted such that it can be send to the microcontroller
export_protocol_to_disk(valves_stack_adj, CFG.EXPORT_PATH_NO_EXT + ".txt")

# The final `valves_stack`, useful for optional post-processing
np.save(CFG.EXPORT_PATH_NO_EXT + "_valves_stack.npy", valves_stack_adj)

# PDFs
idx_last_nonzero_bin = bins.size - np.min(
    (
        np.argmax(np.flipud(pdf_on) > 0),
        np.argmax(np.flipud(pdf_on_adj) > 0),
        np.argmax(np.flipud(pdf_off) > 0),
        np.argmax(np.flipud(pdf_off_adj) > 0),
    )
)
pdfs = np.zeros((idx_last_nonzero_bin, 5))
pdfs[:, 0] = bins[:idx_last_nonzero_bin]
pdfs[:, 1] = pdf_on[:idx_last_nonzero_bin]
pdfs[:, 2] = pdf_on_adj[:idx_last_nonzero_bin]
pdfs[:, 3] = pdf_off[:idx_last_nonzero_bin]
pdfs[:, 4] = pdf_off_adj[:idx_last_nonzero_bin]

np.savetxt(
    CFG.EXPORT_PATH_NO_EXT + "_pdfs.txt",
    pdfs,
    fmt="%.1f\t%.3e\t%.3e\t%.3e\t%.3e",
    header="duration[s]\tpdf_on_orig\tpdf_on_adj\tpdf_off_orig\tpdf_off_adj",
)

# ------------------------------------------------------------------------------
#  Plot
# ------------------------------------------------------------------------------

# 1: Valve and noise animation
# ----------------------------

fig_1 = plt.figure(figsize=(5, 5))
ax = plt.axes()
ax_text = ax.text(0, 1.02, "", transform=ax.transAxes)

# Noise image
# -----------
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

# Valves
# ------
# Create a stack that will contain only the opened valves
valves_plot_pcs_x = np.empty((CFG.N_FRAMES, C.N_VALVES))
valves_plot_pcs_x[:] = np.nan
valves_plot_pcs_y = np.empty((CFG.N_FRAMES, C.N_VALVES))
valves_plot_pcs_y[:] = np.nan

for frame in range(CFG.N_FRAMES):
    for valve in range(C.N_VALVES):
        if valves_stack_adj[frame, valve]:
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

ax.set_aspect("equal", adjustable="box")
ax.set_xlim(C.PCS_X_MIN - 1, C.PCS_X_MAX + 1)
ax.set_ylim(C.PCS_X_MIN - 1, C.PCS_X_MAX + 1)
ax.grid(which="major")
# ax.axis("off")

# Animation function
def animate_fig_1(j):
    ax_text.set_text(f"frame {j:04d}")
    if SHOW_NOISE_IN_PLOT:
        hax_noise.set_data(img_stack_plot[j])
    hax_valves.set_data(valves_plot_pcs_x[j, :], valves_plot_pcs_y[j, :])


# Animate figure
anim = animation.FuncAnimation(
    fig_1,
    animate_fig_1,
    frames=CFG.N_FRAMES,
    interval=CFG.DT_FRAME * 1000,  # [ms]
    init_func=animate_fig_1(0),
)

# 2: Transparencies
# -----------------

fig_2 = plt.figure(2)
fig_2.set_tight_layout(True)
plt.plot(alpha_valves, "deeppink", label=f"valves org {stats_alpha_valves}")
plt.plot(alpha_valves_adj, "k", label=f"valves adj {stats_alpha_valves_adj}")
plt.plot(alpha_noise, "g", label=f"noise {stats_alpha_noise}")
plt.xlim(0, CFG.N_FRAMES)
plt.title("transparency")
plt.xlabel("frame #")
plt.ylabel("alpha [0 - 1]")
plt.legend()

# 3: Probability densities
# ------------------------

# Plot
fig_3, axs = plt.subplots(2)
fig_3.set_tight_layout(True)
move_figure(fig_3, 200, 0)

axs[0].set_title("valve ON")
axs[0].step(bins, pdf_on, "deeppink", where="mid", label="original")
axs[0].step(bins, pdf_on_adj, "k", where="mid", label="adjusted")

axs[1].set_title("valve OFF")
axs[1].step(bins, pdf_off, "deeppink", where="mid", label="original")
axs[1].step(bins, pdf_off_adj, "k", where="mid", label="adjusted")

for ax in axs:
    ax.set_xlabel("duration (s)")
    ax.set_ylabel("PDF")
    ax.set_xlim(0, 6)
    ax.legend()
    ax.grid()

# Round up plots
# --------------

move_figure(fig_1, 0, 0)
move_figure(fig_2, 500, 0)
move_figure(fig_3, 1000, 0)

fig_2.savefig(CFG.EXPORT_PATH_NO_EXT + "_alpha.png")
fig_3.savefig(CFG.EXPORT_PATH_NO_EXT + "_pdfs.png")

# Export animation
# ----------------

if EXPORT_GIF:
    print("Generating gif frames...")
    tick = perf_counter()
    pil_imgs = []
    for frame in trange(CFG.N_FRAMES):
        animate_fig_1(frame)
        pil_img = fig2img_RGB(fig_1)
        pil_imgs.append(pil_img)
    print(f"done in {(perf_counter() - tick):.2f} s\n")

    print("Saving gif...")
    tick = perf_counter()
    pil_imgs[0].save(
        CFG.EXPORT_PATH_NO_EXT + ".gif",
        save_all=True,
        append_images=pil_imgs[1:],
        duration=CFG.DT_FRAME * 1000,  # [ms]
        loop=0,
    )
    print(f"done in {(perf_counter() - tick):.2f} s\n")

plt.show(block=False)
plt.pause(0.001)
input("Press [Enter] to close figures.")
plt.close("all")
