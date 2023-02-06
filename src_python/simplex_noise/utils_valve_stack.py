#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, missing-function-docstring, pointless-string-statement

from typing import Tuple

import numpy as np
from numba import njit


class NoFlanksDetectedException(Exception):
    def __str__(self):
        return "No flanks detected in timeseries"


class MustDebugThisException(Exception):
    def __str__(self):
        return "Should not have happened. Algorithm is wrong."


# ------------------------------------------------------------------------------
#  find_first_downflank
# ------------------------------------------------------------------------------


@njit(
    cache=True,
    nogil=True,
)
def find_first_downflank(array: np.ndarray):
    compare_val = array[0]
    for idx, val in np.ndenumerate(array):
        if val != compare_val:
            if compare_val == 1:
                return idx[0]
            compare_val = 1

    raise NoFlanksDetectedException


# ------------------------------------------------------------------------------
#  detect_segments
# ------------------------------------------------------------------------------


@njit(
    cache=True,
    # parallel=True,  # Don't. Running parallel is detrimental for speed here
    nogil=True,
)
def detect_segments(
    _y: np.ndarray,
) -> Tuple[
    np.ndarray,
    float,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    """The valve timeseries are a closed loop, so we must take special care to
    handle the periodic boundary at the start and end correctly. We do a trick:
    We find the first downflank and roll the timeseries to start at this
    downflank. This shifts the timeseries by `_t_offset`, but makes analyzing
    the HIGH and LOW segments way easier.
    """
    N_frames = _y.size
    _t_offset = find_first_downflank(_y)
    _y = np.roll(_y, -_t_offset)

    # Calculate the segment lengths of valve on/off states
    # ----------------------------------------------------
    # upfl: upflank
    # dnfl: downflank
    _t_upfl = np.where(np.diff(_y) == 1)[0] + 1
    _t_dnfl = np.where(np.diff(_y) == -1)[0] + 1
    _t_dnfl = np.append(0, _t_dnfl)
    _t_dnfl_star = np.append(_t_dnfl[1:], N_frames)

    # Sanity check
    if _t_upfl.size != _t_dnfl.size:
        raise MustDebugThisException

    _seglens_lo = _t_upfl - _t_dnfl
    _seglens_hi = _t_dnfl_star - _t_upfl

    # Sanity check
    if np.sum(_seglens_lo) + np.sum(_seglens_hi) != N_frames:
        raise MustDebugThisException

    return (
        _y,
        _t_offset,
        _t_upfl,
        _t_dnfl,
        _t_dnfl_star,
        _seglens_lo,
        _seglens_hi,
    )


# ------------------------------------------------------------------------------
#  cumulative_histogram
# ------------------------------------------------------------------------------


def cumulative_histogram():
    pass
