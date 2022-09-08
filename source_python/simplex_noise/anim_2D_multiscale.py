#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conda create -n simplex python=3.9
conda activate simplex
pip install ipython numpy numba matplotlib opensimplex pylint black

# Additionally
pip install dvg-devices
"""

from time import perf_counter

from matplotlib import pyplot as plt
from matplotlib import animation
import numpy as np
import opensimplex
from numba import njit, prange

"""
import tracemalloc
tracemalloc.start()
"""

opensimplex.seed(1)
N_pixels = 1000  # Number of pixels on a single axis
N_frames = 200  # Number of time frames

print("Generating noise...", end="")
t0 = perf_counter()

# Generate small-scale noise
SS_x_table = np.linspace(0, 20, N_pixels, endpoint=False)
SS_t_table = np.linspace(0, 10, N_frames, endpoint=False)
img_stack_A = opensimplex.noise3array(SS_x_table, SS_x_table, SS_t_table)

# Generate large-scale noise
LS_x_table = np.linspace(0, 5, N_pixels, endpoint=False)
LS_t_table = np.linspace(0, 10, N_frames, endpoint=False)
img_stack_B = opensimplex.noise3array(LS_x_table, LS_x_table, LS_t_table)

del SS_x_table, SS_t_table
del LS_x_table, LS_t_table

# NOTE: The output range of Simplex noise is [-sqrt(n)/2, sqrt(n)/2], where n is
# the dimensionality
noise3d_range = np.sqrt(3) / 2

elapsed = perf_counter() - t0
print(f" done in {elapsed:.2f} s")
print(f"  min = {np.min(img_stack_A[0]):.3f}")
print(f"  max = {np.max(img_stack_A[0]):.3f}")
print("Rescaling noise... ", end="")
t0 = perf_counter()

# Mix small-scale and large-scale noise together and rescale
img_stack_BW = np.zeros((N_frames, N_pixels, N_pixels), dtype=bool)
alpha = np.zeros(N_frames)  # Grid transparency

for i in range(N_frames):
    # Mix A & B into A
    np.add(img_stack_A[i], img_stack_B[i], out=img_stack_A[i])

    # Rescale noise to [0, 255]
    np.multiply(img_stack_A[i], 64 / noise3d_range, out=img_stack_A[i])
    np.add(img_stack_A[i], 128, out=img_stack_A[i])

    # Calculate grid transparency
    white_pxs = np.where(img_stack_A[i] > 128)
    alpha[i] = len(white_pxs[0]) / N_pixels / N_pixels

    # Binary map
    img_stack_BW[i][white_pxs] = 1

elapsed = perf_counter() - t0
print(f" done in {elapsed:.2f} s")

del img_stack_B

# Plot
fig = plt.figure()
ax = plt.axes()
img = plt.imshow(
    img_stack_A[0],
    cmap="gray",
    vmin=0,
    vmax=255,
    interpolation="none",
)
frame_text = ax.text(0, 1.02, "", transform=ax.transAxes)


def init_anim():
    img.set_data(img_stack_A[0])
    frame_text.set_text("")
    return img, frame_text


def anim(i):
    img.set_data(img_stack_A[i])
    frame_text.set_text("frame %03d, transparency = %.2f" % (i, alpha[i]))
    return img, frame_text


ani = animation.FuncAnimation(
    fig, anim, frames=N_frames, interval=40, init_func=init_anim  # blit=True,
)

plt.grid(False)
plt.axis("off")
plt.show()

fig2 = plt.figure(2)
ax2 = plt.plot(alpha)
plt.xlim(0, N_frames)
plt.title("transparency")
plt.xlabel("frame #")
plt.ylabel("alpha [0 - 1]")
plt.show()

"""
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics("lineno")

print("[ Top 10 ]")
for stat in top_stats[:10]:
    print(stat)
"""
