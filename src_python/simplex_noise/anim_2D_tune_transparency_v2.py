#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint:disable = pointless-string-statement, invalid-name, missing-function-docstring
"""
conda create -n simplex python=3.10
conda activate simplex
pip install -r requirements.txt
"""

from time import perf_counter

import numpy as np
from scipy import optimize
from numba import njit, prange

import matplotlib
from matplotlib import pyplot as plt
from matplotlib import animation

from opensimplex_loops import looping_animated_2D_image

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

img_stack = looping_animated_2D_image(
    N_frames=N_FRAMES,
    N_pixels_x=N_PIXELS,
    t_step=0.1,
    x_step=0.01,
    seed=1,
    dtype=np.float32,
    verbose=True,
)

img_stack_2 = looping_animated_2D_image(
    N_frames=N_FRAMES,
    N_pixels_x=N_PIXELS,
    t_step=0.1,
    x_step=0.005,
    seed=13,
    dtype=np.float32,
    verbose=True,
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
