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
px = np.linspace(0, 10, N_pixels, endpoint=False)
time = np.linspace(0, 10, N_frames, endpoint=False)
img_stack = opensimplex.noise3array(px, px, time)

elapsed = perf_counter() - t0
print(" done in %.2f s" % elapsed)
print("Rescaling noise... ", end="")
t0 = perf_counter()

# Rescale noise
for idx_frame, img in enumerate(img_stack):
    # Rescale noise from [-1, 1] to [0, 255]
    img = np.multiply(img + 1, 128).astype(int)
    img_stack[idx_frame] = img

elapsed = perf_counter() - t0
print(" done in %.2f s" % elapsed)

# Plot
fig = plt.figure()
ax = plt.axes()
img = plt.imshow(img_stack[0], cmap="gray", interpolation="none")
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
