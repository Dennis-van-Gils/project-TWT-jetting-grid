#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint:disable = pointless-string-statement, invalid-name, missing-function-docstring
"""
conda create -n simplex python=3.9
conda activate simplex
pip install ipython numpy numba matplotlib opensimplex==0.4.3

# Additionally
pip install pylint black dvg-devices
"""

from time import perf_counter

import numpy as np
from numba import jit, njit, prange
from matplotlib import pyplot as plt
from matplotlib import animation

from opensimplex.internals import _init as opensimplex_init
from opensimplex.internals import _noise4 as opensimplex_noise4

# ------------------------------------------------------------------------------
#  generate_Simplex2D_closed_timeloop
# ------------------------------------------------------------------------------


@njit(
    "float64[:, :, :](int64, int64, float64, float64, int64[:])",
    cache=True,
    parallel=True,
)
def _generate_Simplex2D_closed_timeloop(
    N_frames: int,
    N_pixels: int,
    t_step: float,
    x_step: float,
    perm: np.ndarray,
) -> np.ndarray:
    t_radius = N_frames * t_step / (2 * np.pi)  # Temporal radius of the loop
    t_factor = 2 * np.pi / N_frames

    noise = np.empty((N_frames, N_pixels, N_pixels), dtype=np.double)
    for t_i in prange(N_frames):  # pylint: disable=not-an-iterable
        t = t_i * t_factor
        t_cos = t_radius * np.cos(t)
        t_sin = t_radius * np.sin(t)
        for y_i in prange(N_pixels):  # pylint: disable=not-an-iterable
            y = y_i * x_step
            for x_i in prange(N_pixels):  # pylint: disable=not-an-iterable
                x = x_i * x_step
                noise[t_i, y_i, x_i] = opensimplex_noise4(
                    x, y, t_sin, t_cos, perm
                )

    return noise


def generate_Simplex2D_closed_timeloop(
    N_frames: int = 200,
    N_pixels: int = 1000,
    t_step: float = 0.1,
    x_step: float = 0.01,
    seed: int = 1,
) -> np.ndarray:
    """Generates Simplex noise as 2D bitmap images that animate over time in a
    closed-loop fashion. I.e., the bitmap image of the last time frame will
    smoothly animate into the bitmap image of the first time frame again. The
    animation path is /not/ a simple reversal of time in order to have the loop
    closed, but rather is a fully unique path from start to finish.

    It does so by calculating Simplex noise in 4 dimensions. The latter two
    dimensions are used to describe a 'circle' in time, in turn used to
    projection map the first two dimensions into bitmap images.

    Args:
        N_frames (int):
            Number of time frames

        N_pixels (int):
            Number of pixels on a single axis

        t_step (float):
            Time step in arb. units. Good values are between 0.02 and 0.2

        x_step (float):
            Spatial step in arb. units. Good values are around 0.01

        seed (int):
            Seed value of the OpenSimplex noise

    Returns:
        The image stack as 3D matrix [time, y-pixel, x-pixel] containing the
        Simplex noise values as a 'grayscale' intensity in floating point.
        The output intensity is garantueed to be in the range [-1, 1], but the
        exact extrema cannot be known a-priori and are most probably way smaller
        than [-1, 1].
    """

    print("Generating noise...", end="")
    tick = perf_counter()

    perm, _ = opensimplex_init(seed)  # The OpenSimplex seed table
    out = _generate_Simplex2D_closed_timeloop(
        N_frames, N_pixels, t_step, x_step, perm
    )

    print(f" done in {(perf_counter() - tick):.2f} s")
    return out


# ------------------------------------------------------------------------------
#  rescale
# ------------------------------------------------------------------------------


def rescale(arr: np.ndarray, symmetrically: bool = True):
    """Rescale noise to [0, 1]
    NOTE: In-place operation on argument `arr`
    """
    # NOTE: Can't seem to get @jit or @njit to work. Fails on `out` parameter of
    # ufuncs `np.divide()` and `np.add()`. Also, `prange` will not go parallel.

    print("Rescaling noise... ", end="")
    tick = perf_counter()

    in_min = np.min(arr)
    in_max = np.max(arr)

    if symmetrically:
        f_norm = max([abs(in_min), abs(in_max)]) * 2
        for i in prange(arr.shape[0]):  # pylint: disable=not-an-iterable
            np.divide(arr[i], f_norm, out=arr[i])
            np.add(arr[i], 0.5, out=arr[i])
    else:
        f_norm = in_max - in_min
        for i in prange(arr.shape[0]):  # pylint: disable=not-an-iterable
            np.subtract(arr[i], in_min, out=arr[i])
            np.divide(arr[i], f_norm, out=arr[i])

    out_min = np.min(arr)
    out_max = np.max(arr)

    print(f" done in {(perf_counter() - tick):.2f} s")
    print(
        f"  from [{in_min:.3f}, {in_max:.3f}] to [{out_min:.3f}, {out_max:.3f}]"
    )


# @njit(
#    cache=True,
#    parallel=True,
# )
def binary_map(
    arr: np.ndarray, BW_threshold: float = 0.5, tune_transparency: float = 0.5
):
    arr_BW = np.zeros(arr.shape)  # , dtype=bool)
    transp = np.zeros(arr.shape[0])  # Transparency

    for i in prange(N_FRAMES):  # pylint: disable=not-an-iterable
        # Tune transparency
        """
        error = 1
        wanted_alpha = 0.3
        # threshold = 0.5
        threshold = 1 - wanted_alpha
        print("---> Frame %d" % i)
        while abs(error) > 0.02:
            white_pxs = np.where(img_stack[i] > threshold)
            alpha[i] = len(white_pxs[0]) / N_PIXELS / N_PIXELS
            error = alpha[i] - wanted_alpha
            print(error)
            if error > 0:
                threshold = threshold + 0.005
            else:
                threshold = threshold - 0.005
        """

        # Calculate transparency
        white_pxs = np.where(arr[i] > 0.5)
        transp[i] = len(white_pxs[0]) / arr.shape[1] / arr.shape[2]

        # Binary map
        arr_BW[i][white_pxs] = 1

    return arr_BW, transp


# ------------------------------------------------------------------------------
#  Main
# ------------------------------------------------------------------------------

N_PIXELS = 1000  # Number of pixels on a single axis
N_FRAMES = 200  # Number of time frames

# Generate noise
img_stack = generate_Simplex2D_closed_timeloop(
    N_pixels=N_PIXELS,
    N_frames=N_FRAMES,
    t_step=0.1,
    x_step=0.01,
)

# Rescale noise
rescale(img_stack, symmetrically=True)

print("More processing... ", end="")
t0 = perf_counter()

img_stack_BW, alpha = binary_map(img_stack)


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
    img.set_data(img_stack[j])
    frame_text.set_text(f"frame {j:03d}, transparency = {alpha[j]:.2f}")
    return img, frame_text


ani = animation.FuncAnimation(
    fig,
    anim,
    frames=N_FRAMES,
    interval=40,
    init_func=init_anim,  # blit=True,
)

# plt.grid(False)
# plt.axis("off")
plt.show()

plt.figure(2)
plt.plot(alpha)
plt.xlim(0, N_FRAMES)
plt.title("transparency")
plt.xlabel("frame #")
plt.ylabel("alpha [0 - 1]")
plt.show()
