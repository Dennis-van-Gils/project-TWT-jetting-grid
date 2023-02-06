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
    y: np.ndarray,
) -> Tuple[
    np.ndarray,
    float,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    """Detect continuous segments inside the valve timeseries where the valve is
    either 'on' or 'off'. The valve timeseries are a closed loop, so we must
    take special care to handle the periodic boundary at the start and end
    correctly. We do a trick: We find the first downflank and roll the
    timeseries to start at this downflank. This shifts the timeseries by
    `t_offset`, but makes analyzing the HIGH and LOW segments way easier.

    Args:
        y (np.ndarray):
            Timeseries of a single valve

    Returns: (Tuple)
        y (np.ndarray):
            Adjusted timeseries of a single valve, rolled forward by `t_offset`.

        t_offset (int):
            Index of the first downflank within the input timeseries.

        t_upfl (np.ndarray):
            Array of indices of detected upflanks, shifted by `t_offset`.

        t_dnfl (np.ndarray):
            Array of indices of detected downflanks, shifted by `t_offset`.
            Zero is appended to the start of the array.

        t_dnfl_star (np.ndarray):
            Array of indices of detected downflanks, shifted by `t_offset`.
            The 'N_frames' index is appended to the end of the array.

        durations_lo (np.ndarray):
            Array containing the duration of each 'valve off' segment.

        durations_hi (np.ndarray):
            Array containing the duration of each 'valve on' segment.
    """
    N_frames = y.size
    t_offset = find_first_downflank(y)
    y = np.roll(y, -t_offset)

    # Calculate the duration of each valve on/off segment
    # ---------------------------------------------------
    # upfl: upflank
    # dnfl: downflank
    t_upfl = np.where(np.diff(y) == 1)[0] + 1
    t_dnfl = np.where(np.diff(y) == -1)[0] + 1
    t_dnfl_star = np.append(t_dnfl, N_frames)
    t_dnfl = np.append(0, t_dnfl)

    # Sanity check
    if t_upfl.size != t_dnfl.size:
        raise MustDebugThisException

    durations_lo = t_upfl - t_dnfl
    durations_hi = t_dnfl_star - t_upfl

    # Sanity check
    if np.sum(durations_lo) + np.sum(durations_hi) != N_frames:
        raise MustDebugThisException

    return (
        y,
        t_offset,
        t_upfl,
        t_dnfl,
        t_dnfl_star,
        durations_lo,
        durations_hi,
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
            durations_lo,
            durations_hi,
        ) = detect_segments(y)

        hist_lo, _ = np.histogram(durations_lo, bins)
        hist_hi, _ = np.histogram(durations_hi, bins)
        np.add(cumul_hist_lo, hist_lo, out=cumul_hist_lo)
        np.add(cumul_hist_hi, hist_hi, out=cumul_hist_hi)

    pdf_lo = cumul_hist_lo / np.sum(cumul_hist_lo)
    pdf_hi = cumul_hist_hi / np.sum(cumul_hist_hi)
    print(f"done in {(perf_counter() - tick):.2f} s\n")

    return pdf_lo, pdf_hi
