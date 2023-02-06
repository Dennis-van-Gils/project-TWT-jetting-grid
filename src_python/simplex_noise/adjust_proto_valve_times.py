#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, missing-function-docstring, pointless-string-statement
# pylint: disable=unused-import

from time import perf_counter

import numpy as np
from matplotlib import pyplot as plt

from utils_matplotlib import move_figure
from utils_valve_stack import detect_segments
import constants as C

# DEBUG info
DEBUG_TIMESERIES_PLOT = False
SHOW_HISTOGRAMS = True


# ------------------------------------------------------------------------------
#  Main
# ------------------------------------------------------------------------------

MIN_SEGMENT_LENGTH = 5
MAX_BIN_VAL = 200

if DEBUG_TIMESERIES_PLOT:
    fig_3 = plt.figure(3)
    fig_3.set_figwidth(8)
    fig_3.set_figheight(4)
    fig_3.set_tight_layout(True)
    move_figure(fig_3, 500, 0)

# Allocate ensemble histograms (i.e. over all valves) of segment lengths
# 'valve on' and 'valve off'
bins = np.arange(0, MAX_BIN_VAL)
cumul_hist_lo_orig = np.zeros(bins.size - 1)
cumul_hist_hi_orig = np.zeros(bins.size - 1)
cumul_hist_lo_adjusted = np.zeros(bins.size - 1)
cumul_hist_hi_adjusted = np.zeros(bins.size - 1)

# Load data from disk
valves_stack = np.asarray(np.load("proto_valves_stack.npy"), dtype=int)

# Timestamps without taking offset into account
t = np.arange(0, C.N_FRAMES)

# Walk over all valves
t_0 = perf_counter()
for valve_idx in np.arange(C.N_VALVES):
    # Retrieve timeseries of single valve
    y = valves_stack[:, valve_idx]
    y_orig = np.copy(y)

    (
        y,
        t_offset_1,
        t_upfl,
        t_dnfl,
        t_dnfl_star,
        seglens_lo,
        seglens_hi,
    ) = detect_segments(y)

    # Histograms of original data
    # ---------------------------
    hist_lo, _ = np.histogram(seglens_lo, bins)
    hist_hi, _ = np.histogram(seglens_hi, bins)
    np.add(cumul_hist_lo_orig, hist_lo, out=cumul_hist_lo_orig)
    np.add(cumul_hist_hi_orig, hist_hi, out=cumul_hist_hi_orig)

    if DEBUG_TIMESERIES_PLOT:
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
    # Remove too short HIGH segments
    for k, seglen in enumerate(seglens_hi):
        if seglen < MIN_SEGMENT_LENGTH:
            y[t_upfl[k] : t_dnfl_star[k]] = 0

    (
        y,
        t_offset_2,
        t_upfl,
        t_dnfl,
        t_dnfl_star,
        seglens_lo,
        seglens_hi,
    ) = detect_segments(y)

    # Remove too short LOW segments
    for k, seglen in enumerate(seglens_lo):
        if seglen < MIN_SEGMENT_LENGTH:
            y[t_dnfl[k] : t_upfl[k]] = 1

    (
        y,
        t_offset_3,
        t_upfl,
        t_dnfl,
        t_dnfl_star,
        seglens_lo,
        seglens_hi,
    ) = detect_segments(y)

    if DEBUG_TIMESERIES_PLOT:
        t_offset = t_offset_3 + t_offset_2
        plt.step(t, np.roll(y, t_offset), "k", where="post", label="adjusted")

        plt.show(block=False)
        plt.pause(0.01)
        # plt.show()
        plt.waitforbuttonpress()

    # Sanity check
    if np.any(seglens_lo < MIN_SEGMENT_LENGTH) or np.any(
        seglens_hi < MIN_SEGMENT_LENGTH
    ):
        raise MustDebugThisException

    # Histograms of adjusted data
    # ---------------------------
    hist_lo_adjusted, _ = np.histogram(seglens_lo, bins)
    hist_hi_adjusted, _ = np.histogram(seglens_hi, bins)
    np.add(cumul_hist_lo_adjusted, hist_lo_adjusted, out=cumul_hist_lo_adjusted)
    np.add(cumul_hist_hi_adjusted, hist_hi_adjusted, out=cumul_hist_hi_adjusted)

    # Roll the timeseries back to its original timings
    # ------------------------------------------------
    t_offset = t_offset_3 + t_offset_2 + t_offset_1
    y = np.roll(y, t_offset)
    t_dnfl = (t_dnfl + t_offset) % C.N_FRAMES
    t_upfl = (t_upfl + t_offset) % C.N_FRAMES

    if DEBUG_TIMESERIES_PLOT:
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


# Cumulative pdfs
# ---------------
pdf_lo = cumul_hist_lo_orig / np.sum(cumul_hist_lo_orig)
pdf_hi = cumul_hist_hi_orig / np.sum(cumul_hist_hi_orig)
pdf_lo_adjusted = cumul_hist_lo_adjusted / np.sum(cumul_hist_lo_adjusted)
pdf_hi_adjusted = cumul_hist_hi_adjusted / np.sum(cumul_hist_hi_adjusted)

print(f"Done in {perf_counter() - t_0:.2f} s")

if SHOW_HISTOGRAMS:
    fig_4, axs = plt.subplots(2)
    fig_4.set_tight_layout(True)
    move_figure(fig_4, 1000, 0)

    axs[0].step(bins[0:-1], pdf_lo, "-r", where="mid", label="off original")
    axs[0].step(
        bins[0:-1], pdf_lo_adjusted, "-k", where="mid", label="off adjusted"
    )
    axs[1].step(bins[0:-1], pdf_hi, "-r", where="mid", label="on original")
    axs[1].step(
        bins[0:-1], pdf_hi_adjusted, "-k", where="mid", label="on adjusted"
    )

    axs[0].set_title("Cumulative PDFs")
    for ax in axs:
        ax.set_xlabel("segment length")
        ax.set_ylabel("PDF")
        ax.set_xlim(0, 60)
        ax.legend()
        ax.grid()

    plt.show()
    # plt.show(block=False)
    # plt.pause(0.01)
    # input("Press [Enter] to end.")
    # plt.close("all")
