#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, missing-function-docstring, pointless-string-statement

from time import perf_counter
from typing import Tuple

import numpy as np
from scipy import optimize
from numba import njit, prange
from tqdm import trange

# ------------------------------------------------------------------------------
#  add_stack_B_to_A
# ------------------------------------------------------------------------------


def add_stack_B_to_A(stack_A: np.ndarray, stack_B: np.ndarray):
    """Add the pixel values of each frame inside stack B to the pixel values of
    the matching frame inside stack A.
    NOTE: In-place operation on argument `stack_A`.
    """
    for i in prange(stack_A.shape[0]):  # pylint: disable=not-an-iterable
        np.add(stack_A[i], stack_B[i], out=stack_A[i])


# ------------------------------------------------------------------------------
#  rescale_stack
# ------------------------------------------------------------------------------


def rescale_stack(stack: np.ndarray, symmetrically: bool = True):
    """Rescale and offset all images in the stack by a single constant gain and
    offset, such that the output image values will lie within the range [0, 1].
    The gain (image contrast) will get maximized in one of two different ways.
    NOTE: In-place operation on argument `stack`.

    Args:
        stack (numpy.ndarray):
            2D image stack [time, y-pixel, x-pixel] containing float values.

        symmetrically (bool, default = True):
            When `True` it will determine the maximum deviation around 0 over
            all frames and rescale the positive upper part and the negative
            lower part of each individual frame by the same gain, ensuring the
            output range becomes either [>0, 1] or [0, <1]. This allows the value
            of 0.5 in the output images to corresponds to 0 in the input images.
            NOTE: Requires the image values to be loosely centered around 0.

            When `False` it will simply maximize the contrast to cover the
            full [0, 1] range.
    """
    # NOTE: Can't seem to get @jit or @njit to work. Fails on `out` parameter of
    # ufuncs `np.divide()` and `np.add()`. Also, `prange` will not go parallel.
    # Addendum: Do not worry about this. The employed numpy ufuncs are optimized
    # incredibly well by numba, regardless. This code outperforms any
    # alternative version using the @jit or @njit decorator on a code
    # block without numpy ufuncs.

    print("Rescaling noise...")
    tick = perf_counter()

    N_frames = stack.shape[0]
    in_min = np.min(stack)
    in_max = np.max(stack)

    if symmetrically:
        f_norm = max([abs(in_min), abs(in_max)]) * 2
        for i in trange(N_frames):  # pylint: disable=not-an-iterable
            np.divide(stack[i], f_norm, out=stack[i])
            np.add(stack[i], 0.5, out=stack[i])
    else:
        f_norm = in_max - in_min
        for i in trange(N_frames):  # pylint: disable=not-an-iterable
            np.subtract(stack[i], in_min, out=stack[i])
            np.divide(stack[i], f_norm, out=stack[i])

    out_min = np.min(stack)
    out_max = np.max(stack)

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
    # NOTE: Can't `njit` on `optimize.newton()`. We use python package
    # `scipy-numba` to get scipy to make use of numba.

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
    1) When `tune_transparency=False` a simple threshold value as given by
       `BW_threshold` is applied. Pixels with a value above `1 - BW_threshold`
       are set to True (1), else False (0).
    2) When `tune_transparency=True` a Newton solver is employed per frame
       to solve for the needed threshold level to achieve a near constant
       transparency over all frames. The given `BW_threshold` value gets now
       interpretted as the transparency value to solve for.

    Transparency is defined as the number of `True` pixels over the total number
    of pixels in the frame.

    Args:
        stack_in (numpy.ndarray):
            2D image stack [time, y-pixel, x-pixel] containing float values.

        BW_threshold (float):
            Either the simple threshold value, or the transparency value [0 - 1]
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
        _binarize_stack_using_threshold(
            stack_in, 1 - BW_threshold, stack_BW, alpha
        )

    print(f"done in {(perf_counter() - tick):.2f} s\n")
    return stack_BW, alpha
