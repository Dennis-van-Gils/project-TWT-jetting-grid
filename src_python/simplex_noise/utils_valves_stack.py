#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utility functions that operate on a `valves_stack`.
"""
__author__ = "Dennis van Gils"
# pylint: disable=invalid-name, missing-function-docstring

from typing import Tuple
from time import perf_counter

import numpy as np
from matplotlib import pyplot as plt

from utils_matplotlib import move_figure


class NoFlanksDetectedException(Exception):
    def __str__(self):
        return "No flanks detected in timeseries"


class MustDebugThisException(Exception):
    def __str__(self):
        return "Should not have happened. Algorithm is wrong."


# ------------------------------------------------------------------------------
#  _find_first_downflank
# ------------------------------------------------------------------------------


# NOTE: Do not @njit()
def _find_first_downflank(array: np.ndarray):
    compare_val = array[0]
    for idx, val in np.ndenumerate(array):
        if val != compare_val:
            if compare_val == 1:
                return idx[0]
            compare_val = 1

    raise NoFlanksDetectedException


# ------------------------------------------------------------------------------
#  _detect_segments
# ------------------------------------------------------------------------------


# NOTE: Do not @njit()
def _detect_segments(
    y: np.ndarray,
) -> Tuple[
    np.ndarray,
    int,
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
    t_offset = _find_first_downflank(y)
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
#  adjust_minimum_valve_durations()
# ------------------------------------------------------------------------------


def adjust_minimum_valve_durations(
    valves_stack_in: np.ndarray, min_valve_duration: int, debug: bool = False
) -> np.ndarray:
    """Adjust the minimum 'valve on' and 'valve off' durations.
    Evenly numbered valves will prefer extending the 'valve off' durations.
    Oddly numbered valves will prefer extending the 'valve on' durations.
    This ensures that we do not deviate too much from the original transparency
    level.

    Args:
        valves_stack_in (np.ndarray):
            Stack containing the boolean states of all valves as 0's and 1's.
            Array shape: [N_frames, N_valves]

        min_valve_duration (int):
            Minimum valve on/off duration [number of frames]. When set to 0 or
            1, no adjustment to the valve durations will be made.

        debug (bool, default=False):
            Useful for debugging. When True will show the before and after
            timeseries plots of each valve highlighting the up- and downflanks.

    Returns:
        valves_stack_out (np.ndarray):
            Stack containing the boolean states of all valves as 0's and 1's.
            Array shape: [N_frames, N_valves]
    """

    if min_valve_duration <= 1:
        print("Adjusting minimum valve durations is skipped\n")
        return valves_stack_in

    print("Adjusting minimum valve durations...")
    tick = perf_counter()

    # Allocate valves stack containing adjusted valve on/off durations
    N_frames, N_valves = valves_stack_in.shape
    valves_stack_out = np.zeros(valves_stack_in.shape, dtype=np.int8)

    # Timestamps without taking offset into account
    t = np.arange(0, N_frames)

    if debug:
        fig_3 = plt.figure(3)
        fig_3.set_figwidth(8)
        fig_3.set_figheight(4)
        fig_3.set_tight_layout(True)
        move_figure(fig_3, 500, 0)

    # Walk over all valves
    for valve_idx in np.arange(N_valves):
        # Retrieve timeseries of single valve
        y = valves_stack_in[:, valve_idx]
        y_orig = np.copy(y)

        (
            y,
            t_offset_1,
            t_upfl,
            t_dnfl,
            t_dnfl_star,
            durations_lo,
            durations_hi,
        ) = _detect_segments(y)

        if debug:
            plt.cla()
            plt.step(t, y, "r", where="post", label="original")
            plt.plot(t_dnfl, np.zeros(t_dnfl.size), "or")
            plt.plot(t_upfl, np.ones(t_upfl.size), "or")
            plt.title(f"A: valve {valve_idx}")
            plt.xlabel(f"frame # + {t_offset_1}")
            plt.ylabel("state [0 - 1]")
            plt.xlim(0, 200)

            plt.show(block=False)
            plt.pause(0.01)

        # Remove smallest segments
        # ------------------------

        if (valve_idx % 2) == 0:
            # Remove too short 'valve on' durations
            for k, seglen in enumerate(durations_hi):
                if seglen < min_valve_duration:
                    y[t_upfl[k] : t_dnfl_star[k]] = 0

            (
                y,
                t_offset_2,
                t_upfl,
                t_dnfl,
                t_dnfl_star,
                durations_lo,
                durations_hi,
            ) = _detect_segments(y)

            # Remove too short 'valve off' durations
            for k, seglen in enumerate(durations_lo):
                if seglen < min_valve_duration:
                    y[t_dnfl[k] : t_upfl[k]] = 1

            (
                y,
                t_offset_3,
                t_upfl,
                t_dnfl,
                t_dnfl_star,
                durations_lo,
                durations_hi,
            ) = _detect_segments(y)
        else:
            # Remove too short 'valve off' durations
            for k, seglen in enumerate(durations_lo):
                if seglen < min_valve_duration:
                    y[t_dnfl[k] : t_upfl[k]] = 1

            (
                y,
                t_offset_3,
                t_upfl,
                t_dnfl,
                t_dnfl_star,
                durations_lo,
                durations_hi,
            ) = _detect_segments(y)

            # Remove too short 'valve on' durations
            for k, seglen in enumerate(durations_hi):
                if seglen < min_valve_duration:
                    y[t_upfl[k] : t_dnfl_star[k]] = 0

            (
                y,
                t_offset_2,
                t_upfl,
                t_dnfl,
                t_dnfl_star,
                durations_lo,
                durations_hi,
            ) = _detect_segments(y)

        if debug:
            t_offset = t_offset_3 + t_offset_2
            plt.step(
                t, np.roll(y, t_offset), "k", where="post", label="adjusted"
            )

            plt.show(block=False)
            plt.pause(0.01)
            # plt.show()
            plt.waitforbuttonpress()

        # Sanity check
        if np.any(durations_lo < min_valve_duration) or np.any(
            durations_hi < min_valve_duration
        ):
            raise MustDebugThisException

        # Roll the timeseries back to its original timings
        # ------------------------------------------------
        t_offset = t_offset_3 + t_offset_2 + t_offset_1
        y = np.roll(y, t_offset)
        t_dnfl = (t_dnfl + t_offset) % N_frames
        t_upfl = (t_upfl + t_offset) % N_frames

        if debug:
            plt.cla()
            plt.step(t, y_orig, "r", where="post", label="original")
            plt.step(t, y, "k", where="post", label="adjusted")
            plt.plot(t_dnfl, np.zeros(t_dnfl.size), "ok")
            plt.plot(t_upfl, np.ones(t_upfl.size), "ok")
            plt.title(f"B: valve {valve_idx}")
            plt.xlabel("frame #")
            plt.ylabel("state [0 - 1]")
            plt.xlim(0, 200)

            plt.show(block=False)
            plt.pause(0.01)
            # plt.show()
            plt.waitforbuttonpress()

        # Store adjusted timeseries
        valves_stack_out[:, valve_idx] = y

    print(f"done in {perf_counter() - tick:.2f} s\n")
    return valves_stack_out


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
            Stack containing the boolean states of all valves as 0's and 1's.
            The array shape should be [N_frames, N_valves].

        bins (np.ndarray):
            The bin centers to calculate the PDF over.

    Returns: (Tuple)
        pdf_valve_on (numpy.ndarray):
            PDF values of the 'valve off' time durations.

        pdf_valve_off (numpy.ndarray):
            PDF values of the 'valve on' time durations.
    """
    # print("Calculating PDFs...")
    # tick = perf_counter()

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
        ) = _detect_segments(y)

        hist_lo, _ = np.histogram(durations_lo, bins)
        hist_hi, _ = np.histogram(durations_hi, bins)
        np.add(cumul_hist_lo, hist_lo, out=cumul_hist_lo)
        np.add(cumul_hist_hi, hist_hi, out=cumul_hist_hi)

    pdf_lo = cumul_hist_lo / np.sum(cumul_hist_lo)
    pdf_hi = cumul_hist_hi / np.sum(cumul_hist_hi)
    # print(f"done in {(perf_counter() - tick):.2f} s\n")

    return pdf_lo, pdf_hi
