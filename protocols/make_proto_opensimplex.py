#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_proto_opensimplex.py

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
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "13-09-2024"
__version__ = "1.0"
# pylint: disable=invalid-name, missing-function-docstring

import sys
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
    generate_OpenSimplex_grayscale_img_stack,
    binarize_img_stack,
    compute_valves_stack,
    export_protocol_to_disk,
)

import constants as C
import config_proto_opensimplex as CFG

# Global flags
EXPORT_GIF = 0  # Export animation as a .gif to disk?
SHOW_NOISE_IN_PLOT = 1  # [0] Only show valves,   [1] Show noise as well
SHOW_NOISE_AS_GRAY = 0  # Show noise as [0] BW,   [1] Grayscale

# Flags useful for developing. Leave both set to False for normal operation.
LOAD_FROM_CACHE = False
SAVE_TO_CACHE = False

# ------------------------------------------------------------------------------
#  Check validity of user configurable parameters
# ------------------------------------------------------------------------------

if (CFG.BW_THRESHOLD is not None and CFG.TARGET_TRANSPARENCY is not None) or (
    CFG.BW_THRESHOLD is None and CFG.TARGET_TRANSPARENCY is None
):
    print(
        "ERROR: Invalid configuration in `config_proto_opensimplex.py`.\n"
        "Either specify `BW_THRESHOLD` or specify `TARGET_TRANSPARENCY`."
    )
    sys.exit(0)

# ------------------------------------------------------------------------------
#  Generate OpenSimplex protocol
# ------------------------------------------------------------------------------

if not LOAD_FROM_CACHE:
    # Generate OpenSimplex grayscale noise
    img_stack_gray = generate_OpenSimplex_grayscale_img_stack()

    if SAVE_TO_CACHE:
        print("Saving cache to disk...")
        tick = perf_counter()
        np.savez("cache.npz", img_stack_gray=img_stack_gray)
        print(f"done in {(perf_counter() - tick):.2f} s\n")

else:
    # Developer: Retrieving data straight from the cache file on disk
    print("Reading cache from disk...")
    tick = perf_counter()
    with np.load("cache.npz", allow_pickle=False) as cache:
        img_stack_gray = cache["img_stack_gray"]
    print(f"done in {(perf_counter() - tick):.2f} s\n")

# Binarize OpenSimplex noise
(
    img_stack_BW,
    alpha_BW,
    alpha_BW_did_converge,
) = binarize_img_stack(img_stack_gray)

# Determine which noise image stack to plot later
if SHOW_NOISE_AS_GRAY:
    img_stack_plot = img_stack_gray
else:
    img_stack_plot = img_stack_BW
    del img_stack_gray  # Not needed anymore -> Free up large chunk of mem

# Map OpenSimplex noise onto valve locations
valves_stack, alpha_valves = compute_valves_stack(img_stack_BW)

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


stats_alpha_BW = build_stats_str(alpha_BW)
stats_alpha_valves = build_stats_str(alpha_valves)
stats_alpha_valves_adj = build_stats_str(alpha_valves_adj)
print("Transparencies (avg ± stdev):")
print(f"  alpha_BW         = {stats_alpha_BW}")
print(f"  alpha_valves     = {stats_alpha_valves}")
print(f"  alpha_valves_adj = {stats_alpha_valves_adj}\n")

# ------------------------------------------------------------------------------
#  Export protocol to disk
# ------------------------------------------------------------------------------

# Protocol formatted such that it can be send to the microcontroller
export_protocol_to_disk(valves_stack_adj, CFG.EXPORT_PATH_NO_EXT + ".proto")

# The final `valves_stack`, useful for optional post-processing
np.save(CFG.EXPORT_PATH_NO_EXT + "_valves_stack.npy", valves_stack_adj)

# The transparencies per frame
with open(CFG.EXPORT_PATH_NO_EXT + "_alpha.txt", "w", encoding="utf-8") as f:
    if CFG.TARGET_TRANSPARENCY is not None:
        f.write("Newton solver was used to solve for a wanted transparency.\n")
        failed_convergences = CFG.N_FRAMES - sum(alpha_BW_did_converge)
        if failed_convergences > 0:
            f.write(f"{failed_convergences:d} frames failed to converge!\n")
        else:
            f.write("All frames did converge.\n")
    else:
        f.write("A simple BW threshold was used.\n")
        f.write("Column `Newton_solver_converged?` can be ignored.\n")

    f.write(
        "\n"
        "# frame\t"
        "transparency_binary_noise\t"
        "transparency_jet_grid\t"
        "Newton_solver_converged?\n"
    )
    for i in range(CFG.N_FRAMES):
        f.write(
            f"{i:d}\t{alpha_BW[i]:.2f}\t"
            f"{alpha_valves_adj[i]:.2f}\t"
            f"{alpha_BW_did_converge[i]!s}\n"
        )

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
    fmt="%.3f\t%.3e\t%.3e\t%.3e\t%.3e",
    header=(
        "duration[s]\t"
        "open_theoretical_valve\t"
        "open_jet_grid_valve\t"
        "closed_theoretical_valve\t"
        "closed_jet_grid_valve"
    ),
)

# ------------------------------------------------------------------------------
#  Plot
# ------------------------------------------------------------------------------

plot_title = f"Protocol: {CFG.EXPORT_FILENAME}"

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
        extent=(
            C.PCS_X_MIN - 1,
            C.PCS_X_MAX + 1,
            C.PCS_X_MIN - 1,
            C.PCS_X_MAX + 1,
        ),
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
    ax_text.set_text(f"frame {j:04d} | {alpha_valves_adj[j]:.2f}")
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
fig_2.set_tight_layout(True)  # type: ignore
fig_2.set_size_inches(12, 4.8)
plt.plot(
    alpha_valves_adj, "deeppink", label=f"Jet grid: {stats_alpha_valves_adj}"
)
# plt.plot(alpha_valves, "g", label=f"Valves org.: {stats_alpha_valves}")
plt.plot(alpha_BW, "k", label=f"Binary noise: {stats_alpha_BW}")
plt.title(plot_title)
plt.xlim(0, CFG.N_FRAMES)
plt.xlabel("Frame #")
plt.ylabel("Transparency [0 - 1]")
plt.minorticks_on()
plt.legend(loc="upper right")

# 3: Probability densities
# ------------------------

# Plot
fig_3, axs = plt.subplots(2)
fig_3.set_tight_layout(True)  # type: ignore

axs[0].set_title(plot_title)
axs[0].set_xlabel("Open duration (s)")
axs[0].step(bins, pdf_on, "k", where="mid", label="Theoretical valve")
axs[0].step(bins, pdf_on_adj, "deeppink", where="mid", label="Jet grid valve")

axs[1].set_xlabel("Closed duration (s)")
axs[1].step(bins, pdf_off, "k", where="mid", label="Theoretical valve")
axs[1].step(bins, pdf_off_adj, "deeppink", where="mid", label="Jet grid valve")

for ax in axs:
    ax.set_ylabel("Discrete PDF")
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
