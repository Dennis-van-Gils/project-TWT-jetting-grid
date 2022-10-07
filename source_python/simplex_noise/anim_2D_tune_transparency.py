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
from typing import Union

import numpy as np
from scipy import optimize
from numba import njit, prange
from numba_progress import ProgressBar
import matplotlib
from matplotlib import pyplot as plt
from matplotlib import animation

from opensimplex.internals import _init as opensimplex_init
from opensimplex.internals import _noise4 as opensimplex_noise4

"""
import linecache
import os
import tracemalloc


def tracemalloc_report(snapshot, key_type="lineno", limit=10):
    # Based on:
    # https://python.readthedocs.io/en/stable/library/tracemalloc.html#pretty-top
    snapshot = snapshot.filter_traces(
        (
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<unknown>"),
        )
    )
    top_stats = snapshot.statistics(key_type)

    print("\nTracemalloc top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        print(
            "#%s: %s:%s: %.1f MiB"
            % (index, filename, frame.lineno, stat.size / 1024 / 1024)
        )
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print("    %s\n" % line)
        else:
            print("")

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f MiB" % (len(other), size / 1024 / 1024))
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f MiB" % (total / 1024 / 1024))


tracemalloc.start()
"""


def move_figure(f, x, y):
    """Move figure's upper left corner to pixel (x, y)"""
    backend = matplotlib.get_backend()
    if backend == "TkAgg":
        f.canvas.manager.window.wm_geometry("+%d+%d" % (x, y))
    elif backend == "WXAgg":
        f.canvas.manager.window.SetPosition((x, y))
    else:
        # This works for QT and GTK
        # You can also use window.setGeometry
        f.canvas.manager.window.move(x, y)


# ------------------------------------------------------------------------------
#  generate_Simplex2D_closed_timeloop
# ------------------------------------------------------------------------------


@njit(
    # "float32[:, :, :](int64, int64, float64, float64, float64, int64[:])",
    cache=True,
    parallel=True,
    nogil=True,
)
def _generate_Simplex2D_closed_timeloop(
    N_frames: int,
    N_pixels: int,
    t_step: float,
    x_step: float,
    y_step: float,
    perm: np.ndarray,
    progress_hook: Union[ProgressBar, None],
) -> np.ndarray:
    t_radius = N_frames * t_step / (2 * np.pi)  # Temporal radius of the loop
    t_factor = 2 * np.pi / N_frames

    noise = np.empty((N_frames, N_pixels, N_pixels), dtype=np.float32)
    for t_i in prange(N_frames):  # pylint: disable=not-an-iterable
        t = t_i * t_factor
        t_cos = t_radius * np.cos(t)
        t_sin = t_radius * np.sin(t)
        if progress_hook is not None:
            progress_hook.update(1)
        for y_i in prange(N_pixels):  # pylint: disable=not-an-iterable
            y = y_i * y_step
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
    y_step: Union[float, None] = None,
    seed: int = 1,
    verbose: bool = True,
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
            Time step in arb. units

        x_step (float):
            Spatial step in arb. units

        y_step (float | None):
            Spatial step in arb. units. When set to None `y_step` will be set
            equal to `x_step`.

        seed (int):
            Seed value of the OpenSimplex noise

        verbose (bool):
            Print 'Generating noise...' progress bar to the terminal?

    Returns:
        The image stack as 3D matrix [time, y-pixel, x-pixel] containing the
        Simplex noise values as a 'grayscale' intensity in floating point.
        The output intensity is garantueed to be in the range [-1, 1], but the
        exact extrema cannot be known a-priori and are most probably way smaller
        than [-1, 1].
    """

    perm, _ = opensimplex_init(seed)  # The OpenSimplex seed table
    if y_step is None:
        y_step = x_step

    if verbose:
        print(f"{'Generating noise...':30s}")  # , end="")
        tick = perf_counter()

        with ProgressBar(total=N_FRAMES, dynamic_ncols=True) as numba_progress:
            out = _generate_Simplex2D_closed_timeloop(
                N_frames, N_pixels, t_step, x_step, y_step, perm, numba_progress
            )

        print(f"done in {(perf_counter() - tick):.2f} s")

    else:
        out = _generate_Simplex2D_closed_timeloop(
            N_frames, N_pixels, t_step, x_step, y_step, perm, None
        )

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

    print(f"{'Rescaling noise...':30s}", end="")
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

    print(f"done in {(perf_counter() - tick):.2f} s")
    print(f"  from [{in_min:+.3f}, {in_max:+.3f}]")
    print(f"  to   [{out_min:+.3f}, {out_max:+.3f}]")


# ------------------------------------------------------------------------------
#  binary_map
# ------------------------------------------------------------------------------


@njit(
    cache=True,
    parallel=True,
)
def _binary_map(
    arr: np.ndarray,
    arr_BW: np.ndarray,
    transp: np.ndarray,
    threshold: float,
):
    """
    NOTE: In-place operation on arguments `arr_BW` and `transp`
    """

    for i in prange(arr.shape[0]):  # pylint: disable=not-an-iterable
        # Calculate transparency
        white_pxs = np.where(arr[i] > threshold)
        transp[i] = len(white_pxs[0]) / arr.shape[1] / arr.shape[2]

        # Binary map
        # Below is the Numba equivalent of: arr_BW[i][white_pxs] = 1
        for j in prange(white_pxs[0].size):  # pylint: disable=not-an-iterable
            arr_BW[i, white_pxs[0][j], white_pxs[1][j]] = 1


def binary_map(arr: np.ndarray, BW_threshold: float = 0.5):
    print(f"{'Binary mapping...':30s}", end="")
    tick = perf_counter()

    arr_BW = np.zeros(arr.shape, dtype=bool)
    transp = np.zeros(arr.shape[0])
    _binary_map(arr, arr_BW, transp, BW_threshold)

    print(f"done in {(perf_counter() - tick):.2f} s")
    return arr_BW, transp


# ------------------------------------------------------------------------------
#  binary_map_with_tuning_newton
# ------------------------------------------------------------------------------


@njit(
    "float64(float64, float32[:, :], float64)",
    cache=True,
    parallel=True,
    nogil=True,
)
def f(x, arr_in, target):
    white_pxs = np.where(arr_in > x)
    return target - len(white_pxs[0]) / arr_in.shape[0] / arr_in.shape[1]


def _binary_map_with_tuning_newton(
    arr: np.ndarray,
    arr_BW: np.ndarray,
    transp: np.ndarray,
    wanted_transp: float,
):
    """
    Using Newton's method to tune transparency:
    https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.newton.html
    NOTE: In-place operation on arguments `arr_BW` and `transp`
    """
    # NOTE: Can't `njit` on `optimize.newton()`

    for i in range(arr.shape[0]):
        # Tune transparency
        # print(i)
        threshold = optimize.newton(
            f,
            1 - wanted_transp,
            args=(arr[i], wanted_transp),
            maxiter=20,
            tol=0.02,
        )

        white_pxs = np.where(arr[i] > threshold)
        transp[i] = len(white_pxs[0]) / arr.shape[1] / arr.shape[2]

        # Binary map
        arr_BW[i][white_pxs] = 1


def binary_map_with_tuning_newton(arr: np.ndarray, tuning_transp=0.5):
    print(f"{'Binary mapping and newton...':30s}", end="")
    tick = perf_counter()

    arr_BW = np.zeros(arr.shape, dtype=bool)
    transp = np.zeros(arr.shape[0])
    _binary_map_with_tuning_newton(arr, arr_BW, transp, tuning_transp)

    print(f"done in {(perf_counter() - tick):.2f} s")
    return arr_BW, transp


# ------------------------------------------------------------------------------
#  binary_map_with_tuning
# ------------------------------------------------------------------------------


@njit(
    parallel=True,
)
def _binary_map_with_tuning(
    arr: np.ndarray,
    arr_BW: np.ndarray,
    transp: np.ndarray,
    wanted_transp: float,
):
    """
    NOTE: In-place operation on arguments `arr_BW` and `transp`
    TODO: Add `reached max-iteration` warning with escape
    """

    for i in prange(arr.shape[0]):  # pylint: disable=not-an-iterable
        # Tune transparency
        error = 1
        threshold = 1 - wanted_transp
        # print(i)
        while abs(error) > 0.02:
            white_pxs = np.where(arr[i] > threshold)
            transp[i] = len(white_pxs[0]) / arr.shape[1] / arr.shape[2]
            error = transp[i] - wanted_transp
            # print(error)
            """
            if abs(error) > 0.2:
                threshold += 0.01 if error > 0 else -0.01
            elif abs(error) > 0.1:
                threshold += 0.005 if error > 0 else -0.005
            elif abs(error) > 0.5:
                threshold += 0.0025 if error > 0 else -0.0025
            else:
                threshold += 0.001 if error > 0 else -0.001
            """
            threshold += 0.005 if error > 0 else -0.005

        # Binary map
        # Below is the Numba equivalent of: arr_BW[i][white_pxs] = 1
        for j in prange(white_pxs[0].size):  # pylint: disable=not-an-iterable
            arr_BW[i, white_pxs[0][j], white_pxs[1][j]] = 1


def binary_map_with_tuning(arr: np.ndarray, tuning_transp=0.5):
    print(f"{'Binary mapping and tuning...':30s}", end="")
    tick = perf_counter()

    arr_BW = np.zeros(arr.shape, dtype=bool)
    transp = np.zeros(arr.shape[0])
    _binary_map_with_tuning(arr, arr_BW, transp, tuning_transp)

    print(f"done in {(perf_counter() - tick):.2f} s")
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
    seed=1,
)

img_stack_2 = generate_Simplex2D_closed_timeloop(
    N_pixels=N_PIXELS,
    N_frames=N_FRAMES,
    t_step=0.1,
    x_step=0.005,
    seed=13,
)

# Add A & B into A
for i in prange(N_FRAMES):  # pylint: disable=not-an-iterable
    np.add(img_stack[i], img_stack_2[i], out=img_stack[i])

# Rescale noise
rescale(img_stack, symmetrically=False)

# Map into binary and calculate transparency
# img_stack_BW, alpha = binary_map(img_stack)
# img_stack_BW, alpha = binary_map_with_tuning(img_stack, tuning_transp=0.6)
img_stack_BW, alpha = binary_map_with_tuning_newton(
    img_stack, tuning_transp=0.6
)

# ------------------------------------------------------------------------------
#  Plot
# ------------------------------------------------------------------------------

fig_1 = plt.figure()
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
    fig_1,
    anim,
    frames=N_FRAMES,
    interval=40,
    init_func=init_anim,  # blit=True,
)

# plt.grid(False)
# plt.axis("off")
move_figure(fig_1, 0, 0)

fig_2 = plt.figure(2)
plt.plot(alpha)
plt.xlim(0, N_FRAMES)
plt.title("transparency")
plt.xlabel("frame #")
plt.ylabel("alpha [0 - 1]")
move_figure(fig_2, 720, 0)

"""
tracemalloc_report(tracemalloc.take_snapshot(), limit=4)
"""

plt.show()
