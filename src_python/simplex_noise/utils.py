#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, missing-function-docstring, pointless-string-statement

from time import perf_counter
from typing import Tuple

import numpy as np
from scipy import optimize
from numba import njit, prange
from tqdm import trange

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

    print("Rescaling noise...")
    tick = perf_counter()

    in_min = np.min(arr)
    in_max = np.max(arr)

    if symmetrically:
        f_norm = max([abs(in_min), abs(in_max)]) * 2
        for i in trange(arr.shape[0]):  # pylint: disable=not-an-iterable
            np.divide(arr[i], f_norm, out=arr[i])
            np.add(arr[i], 0.5, out=arr[i])
    else:
        f_norm = in_max - in_min
        for i in trange(arr.shape[0]):  # pylint: disable=not-an-iterable
            np.subtract(arr[i], in_min, out=arr[i])
            np.divide(arr[i], f_norm, out=arr[i])

    out_min = np.min(arr)
    out_max = np.max(arr)

    print(f"from [{in_min:+.3f}, {in_max:+.3f}]")
    print(f"to   [{out_min:+.3f}, {out_max:+.3f}]")
    print(f"done in {(perf_counter() - tick):.2f} s\n")


# ------------------------------------------------------------------------------
#  binarize_stack
# ------------------------------------------------------------------------------


@njit(
    cache=True,
    parallel=True,
    nogil=True,
)
def _binarize_stack_using_threshold(
    stack_in: np.ndarray,
    threshold: float,
    stack_BW: np.ndarray,
    alpha: np.ndarray,
):
    """NOTE: In-place operation on arguments `stack_BW` and `alpha`"""
    for i in prange(stack_in.shape[0]):  # pylint: disable=not-an-iterable
        true_pxs = np.where(stack_in[i] > threshold)
        alpha[i] = len(true_pxs[0]) / stack_in.shape[1] / stack_in.shape[2]
        # Below is the Numba equivalent of: stack_BW[i][true_pxs] = 1
        for j in prange(true_pxs[0].size):  # pylint: disable=not-an-iterable
            stack_BW[i, true_pxs[0][j], true_pxs[1][j]] = 1


@njit(
    cache=True,
    parallel=True,
    nogil=True,
)
def newton_fun(x, arr_in, target):
    true_pxs = np.where(arr_in > x)
    return target - len(true_pxs[0]) / arr_in.shape[0] / arr_in.shape[1]


def _binarize_stack_using_newton(
    stack_in: np.ndarray,
    wanted_transparency: float,
    stack_BW: np.ndarray,
    alpha: np.ndarray,
):
    """Using Newton's method to solve for the given transparency:
    https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.newton.html
    NOTE: In-place operation on arguments `stack_BW` and `alpha`
    """
    # NOTE: Can't `njit` on `optimize.newton()`

    for i in trange(stack_in.shape[0]):
        # Solve for transparency
        threshold = optimize.newton(
            newton_fun,
            1 - wanted_transparency,
            args=(stack_in[i], wanted_transparency),
            maxiter=20,
            tol=0.02,
        )

        true_pxs = np.where(stack_in[i] > threshold)
        alpha[i] = len(true_pxs[0]) / stack_in.shape[1] / stack_in.shape[2]
        stack_BW[i][true_pxs] = 1


def binarize_stack(
    stack_in: np.ndarray, BW_threshold: float, tune_transparency: bool
) -> Tuple[np.ndarray, np.ndarray]:
    """Binarize each frame of the image stack.

    Two methods are possible:
    1) When `tune_transparency` == False, a simple threshold value as given by
       `BW_threshold` is applied. Pixels with a value above this threshold are
       set to True (1), otherwise False (0).
    2) When `tune_transparency` == True, a Newton solver is employed per frame
       to solve for the needed threshold level to achieve a near constant
       transparency over all frames. The given `BW_threshold` value gets now
       interpretted as the transparency value to solve for.

    Transparency is defined as the number of `True` pixels over the total number
    of pixels in the frame.

    Args:
        stack_in (numpy.ndarray):
            2D image stack [time, y-pixel, x-pixel] containing float values.

        BW_threshold (float):
            Either the simple threshold value or the transparency value [0 - 1]
            to solve for, see above.

        tune_transparency (bool):
            See above.

    Returns: (Tuple)
        stack_BW (numpy.ndarray):
            2D image stack [time, y-pixel, x-pixel] containing boolean values.

        alpha (numpy.ndarray):
            1D array containing the effective transparency of each frame.
    """
    tick = perf_counter()
    stack_BW = np.zeros(stack_in.shape, dtype=bool)
    alpha = np.zeros(stack_in.shape[0])

    if tune_transparency:
        print("Binarizing noise and tuning transparency...")
        _binarize_stack_using_newton(stack_in, BW_threshold, stack_BW, alpha)
    else:
        print("Binarizing noise...")
        _binarize_stack_using_threshold(stack_in, BW_threshold, stack_BW, alpha)

    print(f"done in {(perf_counter() - tick):.2f} s\n")
    return stack_BW, alpha
