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

opensimplex.seed(1)
N_pixels = 1000  # Number of pixels on a single axis
N_frames = 200  # Number of time frames

print("Generating noise...", end="")
t0 = perf_counter()

# Generate noise
x_table = np.linspace(0, 10, N_pixels, endpoint=False)  # Spatial axis
t_table = np.linspace(0, 10, N_frames, endpoint=False)  # Temporal axis
img_stack = opensimplex.noise3array(x_table, x_table, t_table)

# NOTE: The output range of Simplex noise is [-sqrt(n)/2, sqrt(n)/2], where n is
# the dimensionality
noise3d_range = np.sqrt(3) / 2

elapsed = perf_counter() - t0
print(f" done in {elapsed:.2f} s")
print(f"  min = {np.min(img_stack[0]):.3f}")
print(f"  max = {np.max(img_stack[0]):.3f}")
print("Rescaling noise... ", end="")
t0 = perf_counter()

# Rescale noise to [0, 255]
for i in range(N_frames):
    np.multiply(img_stack[i], 128 / noise3d_range, out=img_stack[i])
    np.add(img_stack[i], 128, out=img_stack[i])

elapsed = perf_counter() - t0
print(f" done in {elapsed:.2f} s")

# Plot
fig = plt.figure()
ax = plt.axes()
img = plt.imshow(
    img_stack[0],
    cmap="gray",
    vmin=0,
    vmax=255,
    interpolation="none",
)
frame_text = ax.text(0, 1.02, "", transform=ax.transAxes)


def init_anim():
    img.set_data(img_stack[0])
    frame_text.set_text("")
    return img, frame_text


def anim(i):
    img.set_data(img_stack[i])
    frame_text.set_text("frame %d" % i)
    return img, frame_text


ani = animation.FuncAnimation(
    fig, anim, frames=N_frames, interval=40, init_func=init_anim  # blit=True,
)

plt.grid(False)
plt.axis("off")
plt.show()
