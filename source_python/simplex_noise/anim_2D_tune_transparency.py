#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint:disable = pointless-string-statement, invalid-name, missing-function-docstring
"""
conda create -n simplex python=3.9
conda activate simplex
pip install ipython numpy numba matplotlib opensimplex pylint black

# Additionally
pip install dvg-devices
"""

# NOTE: Memory consumption is gigantic for 4-D Simplex noise to generate as a
# continuous matrix. Hence, we'll have to iterate the points on request.

from time import perf_counter

from matplotlib import pyplot as plt
from matplotlib import animation
import numpy as np
from numba import njit, prange
from opensimplex.internals import _init, _noise4

# opensimplex.seed(1)
perm, foo = _init(1)
N_pixels = 1000  # Number of pixels on a single axis
N_frames = 600  # Number of time frames
t_radius = 9  # Temporal radius of the time loop


@njit(cache=True, parallel=True)
def generate_noise(
    N_frames_: int,
    N_pixels_: int,
    t_radius_: float,
    x_table_: np.ndarray,
    perm_: np.ndarray,
):
    noise = np.empty((1, N_frames, N_pixels, N_pixels), dtype=np.double)
    t_factor = 2 * np.pi / N_frames_
    for t_i in prange(N_frames_):  # pylint: disable=not-an-iterable
        t = t_i * t_factor
        t_cos = t_radius_ * np.cos(t)
        t_sin = t_radius_ * np.sin(t)
        for y_i in prange(N_pixels_):  # pylint: disable=not-an-iterable
            for x_i in prange(N_pixels_):  # pylint: disable=not-an-iterable
                noise[0, t_i, y_i, x_i] = _noise4(
                    x_table_[x_i], x_table_[y_i], t_sin, t_cos, perm_
                )

    return noise[0]  # Ditches the dummy dimension


print("Generating noise...", end="")
t0 = perf_counter()

# Generate noise
x_table = np.linspace(0, 10, N_pixels, endpoint=False)  # Spatial axis
img_stack = generate_noise(N_frames, N_pixels, t_radius, x_table, perm)
img_stack_min = np.min(img_stack)
img_stack_max = np.max(img_stack)

elapsed = perf_counter() - t0
print(f" done in {elapsed:.2f} s")
print(f"  min = {img_stack_min:.3f}")
print(f"  max = {img_stack_max:.3f}")
print("Rescaling noise... ", end="")
t0 = perf_counter()

# Rescale noise symmetrically to [0, 1]
img_stack_BW = np.zeros((N_frames, N_pixels, N_pixels), dtype=bool)
alpha = np.zeros(N_frames)  # Grid transparency
f_norm = max([abs(img_stack_min), abs(img_stack_max)]) * 2
for i in prange(N_frames):  # pylint: disable=not-an-iterable
    np.divide(img_stack[i], f_norm, out=img_stack[i])
    np.add(img_stack[i], 0.5, out=img_stack[i])

    # And tune transparency
    d_alpha = 1
    wanted_alpha = 0.3
    # threshold = 0.5
    threshold = 1 - wanted_alpha
    print("---> Frame %d" % i)
    while abs(d_alpha) > 0.02:
        white_pxs = np.where(img_stack[i] > threshold)
        alpha[i] = len(white_pxs[0]) / N_pixels / N_pixels
        d_alpha = alpha[i] - wanted_alpha
        # print(d_alpha)
        if d_alpha > 0:
            threshold = threshold + 0.002
        else:
            threshold = threshold - 0.002

    # Calculate grid transparency
    # white_pxs = np.where(img_stack[i] > 0.5)
    # alpha[i] = len(white_pxs[0]) / N_pixels / N_pixels

    # Binary map
    img_stack_BW[i][white_pxs] = 1

img_stack_min = np.min(img_stack)
img_stack_max = np.max(img_stack)

elapsed = perf_counter() - t0
print(f" done in {elapsed:.2f} s")
print(f"  min = {img_stack_min:.3f}")
print(f"  max = {img_stack_max:.3f}")

# ------------------------------------------------------------------------------
#  Plot
# ------------------------------------------------------------------------------

fig = plt.figure()
ax = plt.axes()
img = plt.imshow(
    img_stack[0],
    cmap="gray",
    vmin=0,
    vmax=1,
    interpolation="none",
)
frame_text = ax.text(0, 1.02, "", transform=ax.transAxes)


def init_anim():
    img.set_data(img_stack[0])
    frame_text.set_text("")
    return img, frame_text


def anim(j):
    img.set_data(img_stack_BW[j])
    frame_text.set_text(f"frame {j:03d}, transparency = {alpha[j]:.2f}")
    return img, frame_text


ani = animation.FuncAnimation(
    fig,
    anim,
    frames=N_frames,
    interval=40,
    init_func=init_anim,  # blit=True,
)

plt.grid(False)
plt.axis("off")
plt.show()

plt.figure(2)
plt.plot(alpha)
plt.xlim(0, N_frames)
plt.title("transparency")
plt.xlabel("frame #")
plt.ylabel("alpha [0 - 1]")
plt.show()
