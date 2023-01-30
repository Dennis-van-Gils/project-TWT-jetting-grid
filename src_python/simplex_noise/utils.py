#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, missing-function-docstring, pointless-string-statement

from time import perf_counter

import numpy as np
from scipy import optimize
from numba import njit, prange

import matplotlib


def move_figure(f, x, y):
    """Move figure's upper left corner to pixel (x, y)"""
    backend = matplotlib.get_backend()
    if backend == "TkAgg":
        f.canvas.manager.window.wm_geometry(f"+{x}+{y}")
    elif backend == "WXAgg":
        f.canvas.manager.window.SetPosition((x, y))
    else:
        # This works for QT and GTK
        # You can also use window.setGeometry
        f.canvas.manager.window.move(x, y)


# ------------------------------------------------------------------------------
#  add_stack_B_to_A
# ------------------------------------------------------------------------------


def add_stack_B_to_A(stack_A: np.ndarray, stack_B: np.ndarray):
    """Add B to A"""
    for i in prange(np.size(stack_A, 0)):  # pylint: disable=not-an-iterable
        np.add(stack_A[i], stack_B[i], out=stack_A[i])


# ------------------------------------------------------------------------------
#  rescale_stack
# ------------------------------------------------------------------------------


def rescale_stack(arr: np.ndarray, symmetrically: bool = True):
    """Rescale noise to [0, 1]
    NOTE: In-place operation on argument `arr`
    """
    # NOTE: Can't seem to get @jit or @njit to work. Fails on `out` parameter of
    # ufuncs `np.divide()` and `np.add()`. Also, `prange` will not go parallel.

    print(f"{'Rescaling noise...':32s}", end="")
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
    """NOTE: In-place operation on arguments `arr_BW` and `transp`"""

    for i in prange(arr.shape[0]):  # pylint: disable=not-an-iterable
        # Calculate transparency
        white_pxs = np.where(arr[i] > threshold)
        transp[i] = len(white_pxs[0]) / arr.shape[1] / arr.shape[2]

        # Binary map
        # Below is the Numba equivalent of: arr_BW[i][white_pxs] = 1
        for j in prange(white_pxs[0].size):  # pylint: disable=not-an-iterable
            arr_BW[i, white_pxs[0][j], white_pxs[1][j]] = 1


def binary_map(arr: np.ndarray, BW_threshold: float = 0.5):
    print(f"{'Binary mapping...':32s}", end="")
    tick = perf_counter()

    arr_BW = np.zeros(arr.shape, dtype=bool)
    transp = np.zeros(arr.shape[0])
    _binary_map(arr, arr_BW, transp, BW_threshold)

    print(f"done in {(perf_counter() - tick):.2f} s")
    return arr_BW, transp


# ------------------------------------------------------------------------------
#  binary_map_tune_transparency
# ------------------------------------------------------------------------------


@njit(
    cache=True,
    parallel=True,
    nogil=True,
)
def newton_fun(x, arr_in, target):
    white_pxs = np.where(arr_in > x)
    return target - len(white_pxs[0]) / arr_in.shape[0] / arr_in.shape[1]


def _binary_map_tune_transparency(
    arr: np.ndarray,
    arr_BW: np.ndarray,
    transp: np.ndarray,
    wanted_transp: float,
):
    """Using Newton's method to tune transparency:
    https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.newton.html
    NOTE: In-place operation on arguments `arr_BW` and `transp`
    """
    # NOTE: Can't `njit` on `optimize.newton()`

    for i in range(arr.shape[0]):
        # Tune transparency
        # print(i)
        threshold = optimize.newton(
            newton_fun,
            1 - wanted_transp,
            args=(arr[i], wanted_transp),
            maxiter=20,
            tol=0.02,
        )

        white_pxs = np.where(arr[i] > threshold)
        transp[i] = len(white_pxs[0]) / arr.shape[1] / arr.shape[2]

        # Binary map
        arr_BW[i][white_pxs] = 1


def binary_map_tune_transparency(arr: np.ndarray, tuning_transp=0.5):
    print(f"{'BW map & transparency tuning...':32s}", end="")
    tick = perf_counter()

    arr_BW = np.zeros(arr.shape, dtype=bool)
    transp = np.zeros(arr.shape[0])
    _binary_map_tune_transparency(arr, arr_BW, transp, tuning_transp)

    print(f"done in {(perf_counter() - tick):.2f} s")
    return arr_BW, transp
