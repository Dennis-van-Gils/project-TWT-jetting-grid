#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, missing-function-docstring, pointless-string-statement

from typing import Tuple
from time import perf_counter

import numpy as np


class NoFlanksDetectedException(Exception):
    def __str__(self):
        return "No flanks detected in timeseries"


class MustDebugThisException(Exception):
    def __str__(self):
        return "Should not have happened. Algorithm is wrong."


# ------------------------------------------------------------------------------
#  find_first_downflank
# ------------------------------------------------------------------------------


# NOTE: Do not @njit()
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

# NOTE: Do not @njit()
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
#  valve_on_off_PDFs
# ------------------------------------------------------------------------------

# NOTE: Do not @njit()
def valve_on_off_PDFs(
    valves_stack: np.ndarray, bins: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate the cumulative (i.e. taken over all valves) probability
    density functions (PDFs) of the 'valve on' and 'valve off' time durations.

    Args:
        valves_stack (np.ndarray):
            Stack containing the boolean states of all valves. The array shape
            should be [N_frames, N_valves].

        bins (np.ndarray):
            The bin centers to calculate the PDF over.

    Returns: (Tuple)
        pdf_valve_on (numpy.ndarray):
            PDF values of the 'valve off' time durations.

        pdf_valve_off (numpy.ndarray):
            PDF values of the 'valve on' time durations.
    """
    print("Calculating PDFs...")
    tick = perf_counter()

    # Allocate cumulative histograms
    cumul_hist_lo = np.zeros(bins.size - 1)
    cumul_hist_hi = np.zeros(bins.size - 1)

    # Walk over all valves
    N_valves = valves_stack.shape[1]
    for valve_idx in np.arange(N_valves):
        # Retrieve timeseries of single valve
        y = valves_stack[:, valve_idx]

        (
            y,
            _,
            _,
            _,
            _,
            seglens_lo,
            seglens_hi,
        ) = detect_segments(y)

        hist_lo, _ = np.histogram(seglens_lo, bins)
        hist_hi, _ = np.histogram(seglens_hi, bins)
        np.add(cumul_hist_lo, hist_lo, out=cumul_hist_lo)
        np.add(cumul_hist_hi, hist_hi, out=cumul_hist_hi)

    pdf_lo = cumul_hist_lo / np.sum(cumul_hist_lo)
    pdf_hi = cumul_hist_hi / np.sum(cumul_hist_hi)
    print(f"done in {(perf_counter() - tick):.2f} s\n")

    return pdf_lo, pdf_hi
