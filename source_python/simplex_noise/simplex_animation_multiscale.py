#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conda create -n simplex python=3.9
conda activate simplex
pip install ipython numpy numba matplotlib opensimplex pylint black

# Additionally
pip install dvg-devices
"""

from matplotlib import pyplot as plt
from matplotlib import animation
import numpy as np
from numba import njit
import opensimplex
from time import perf_counter

opensimplex.seed(1)
N_pixels = 1000  # Number of pixels on a single axis
N_frames = 200  # Number of time frames

print("Generating noise...", end="")
t0 = perf_counter()

# Generate large-scale noise
LS_px = np.linspace(0, 5, N_pixels, endpoint=False)
LS_time = np.linspace(0, 10, N_frames, endpoint=False)
LS_img_stack = opensimplex.noise3array(LS_px, LS_px, LS_time)

# Generate small-scale noise
SS_px = np.linspace(0, 20, N_pixels, endpoint=False)
SS_time = np.linspace(0, 10, N_frames, endpoint=False)
SS_img_stack = opensimplex.noise3array(SS_px, SS_px, SS_time)

elapsed = perf_counter() - t0
print(" done in %.2f s" % elapsed)
print("Mixing noise...    ", end="")
t0 = perf_counter()

# Mix small-scale and large-scale noise together and rescale
img_stack = np.empty((N_frames, N_pixels, N_pixels), dtype=int)
img_stack_BW = np.zeros((N_frames, N_pixels, N_pixels), dtype=int)
alpha = np.zeros(N_frames)  # Grid transparency
for idx_frame, img in enumerate(SS_img_stack):
    # Mix
    np.add(img, LS_img_stack[idx_frame], out=img)
    np.divide(img, 2, out=img)

    # Calculate grid transparency
    alpha[idx_frame] = np.sum(img > 0) / N_pixels / N_pixels

    # Rescale noise from [-1, 1] to [0, 255]
    np.add(img, 1, out=img)
    np.multiply(img, 128, out=img)
    img = img.astype(int)

    img_stack[idx_frame] = img
    img_stack_BW[idx_frame][np.where(img > 128)] = 255

elapsed = perf_counter() - t0
print(" done in %.2f s" % elapsed)

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
