#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, missing-function-docstring, pointless-string-statement
# pylint: disable=unused-import

from time import perf_counter

import numpy as np
from matplotlib import pyplot as plt

from utils_matplotlib import move_figure
from utils_valve_stack import (
    detect_segments,
    valve_on_off_PDFs,
    MustDebugThisException,
)
import constants as C

# DEBUG info
DEBUG_TIMESERIES_PLOT = False

# ------------------------------------------------------------------------------
#  Main
# ------------------------------------------------------------------------------

MIN_VALVE_DURATION = 5
MAX_BIN_VAL = 200

print("Adjusting valve times...")
tick = perf_counter()

if DEBUG_TIMESERIES_PLOT:
    fig_3 = plt.figure(3)
    fig_3.set_figwidth(8)
    fig_3.set_figheight(4)
    fig_3.set_tight_layout(True)
    move_figure(fig_3, 500, 0)

# Load data from disk
valves_stack = np.asarray(np.load("proto_valves_stack.npy"), dtype=int)

# Allocate adjusted valves_stack
valves_stack_star = np.zeros(valves_stack.shape)

# Timestamps without taking offset into account
t = np.arange(0, C.N_FRAMES)

# Walk over all valves
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
        durations_lo,
        durations_hi,
    ) = detect_segments(y)

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
    # Remove too short 'valve on' durations
    for k, seglen in enumerate(durations_hi):
        if seglen < MIN_VALVE_DURATION:
            y[t_upfl[k] : t_dnfl_star[k]] = 0

    (
        y,
        t_offset_2,
        t_upfl,
        t_dnfl,
        t_dnfl_star,
        durations_lo,
        durations_hi,
    ) = detect_segments(y)

    # Remove too short 'valve off' durations
    for k, seglen in enumerate(durations_lo):
        if seglen < MIN_VALVE_DURATION:
            y[t_dnfl[k] : t_upfl[k]] = 1

    (
        y,
        t_offset_3,
        t_upfl,
        t_dnfl,
        t_dnfl_star,
        durations_lo,
        durations_hi,
    ) = detect_segments(y)

    if DEBUG_TIMESERIES_PLOT:
        t_offset = t_offset_3 + t_offset_2
        plt.step(t, np.roll(y, t_offset), "k", where="post", label="adjusted")

        plt.show(block=False)
        plt.pause(0.01)
        # plt.show()
        plt.waitforbuttonpress()

    # Sanity check
    if np.any(durations_lo < MIN_VALVE_DURATION) or np.any(
        durations_hi < MIN_VALVE_DURATION
    ):
        raise MustDebugThisException

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

    # Store adjusted timeseries
    valves_stack_star[:, valve_idx] = y

print(f"done in {perf_counter() - tick:.2f} s\n")

# ------------------------------------------------------------------------------
#  Plot PDFs
# ------------------------------------------------------------------------------

bins = np.arange(0, MAX_BIN_VAL)
pdf_off_1, pdf_on_1 = valve_on_off_PDFs(valves_stack, bins)
pdf_off_2, pdf_on_2 = valve_on_off_PDFs(valves_stack_star, bins)

fig_4, axs = plt.subplots(2)
fig_4.set_tight_layout(True)
move_figure(fig_4, 1000, 0)

axs[0].set_title("valve OFF")
axs[0].step(bins[0:-1], pdf_off_1, "-r", where="mid", label="original")
axs[0].step(bins[0:-1], pdf_off_2, "-k", where="mid", label="adjusted")

axs[1].set_title("valve ON")
axs[1].step(bins[0:-1], pdf_on_1, "-r", where="mid", label="original")
axs[1].step(bins[0:-1], pdf_on_2, "-k", where="mid", label="adjusted")

for ax in axs:
    ax.set_xlabel("duration")
    ax.set_ylabel("PDF")
    ax.set_xlim(0, 60)
    ax.legend()
    ax.grid()

plt.show()
# plt.show(block=False)
# plt.pause(0.01)
# input("Press [Enter] to end.")
# plt.close("all")
