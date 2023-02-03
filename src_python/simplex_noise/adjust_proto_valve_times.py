#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, missing-function-docstring, pointless-string-statement
# pylint: disable=unused-import

import sys
from time import perf_counter

import numpy as np
from tqdm import trange
from numba import njit, prange

from matplotlib import pyplot as plt

plt.rcParams["figure.figsize"] = [5, 4]

from utils import move_figure
import constants as C


class NoFlanksDetectedException(Exception):
    def __str__(self):
        return "No flanks detected in timeseries"


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
#  Main
# ------------------------------------------------------------------------------

valves_stack = np.asarray(np.load("proto_valves_stack.npy"), dtype=int)

fig_3 = plt.figure(3)
fig_3.set_tight_layout(True)
move_figure(fig_3, 500, 0)

bins = np.arange(0, 200)
cumul_hist_lo = np.zeros(bins.size - 1)
cumul_hist_hi = np.zeros(bins.size - 1)

for i in np.arange(C.N_VALVES):
    # Load timeseries of valve
    y = valves_stack[:, i]

    # The timeseries are a closed loop, so we do a trick.
    # We shift all timeseries to let them start at the first downflank.
    # -----------------------------------------------------------------
    y = np.concatenate((y, y))
    t_offset = find_first_downflank(y)
    y = y[t_offset : t_offset + C.N_FRAMES]

    # Timestamps without taking offset into account
    t = np.arange(0, C.N_FRAMES)

    # Calculate the segment lengths of valve on/off states
    # ----------------------------------------------------
    # ufl: upflank
    # dfl: downflank
    t_ufl = np.where(np.diff(y) == 1)[0]
    t_dfl = np.where(np.diff(y) == -1)[0]
    t_dfl = np.append(t_dfl, C.N_FRAMES - 1)

    seglen_hi = t_dfl - t_ufl
    seglen_lo = t_ufl - np.concatenate(((0,), t_dfl[:-1]))

    if 1:
        print(
            f"{t_offset:4d}  {t_dfl.size:4d}  {t_ufl.size:4d}  "
            f"{t_dfl.size==t_ufl.size:6}  ",
            f"{np.max(seglen_hi):4d}  {np.max(seglen_lo):4d}",
        )

    # Histograms
    # ----------
    hist_lo, _ = np.histogram(seglen_lo, bins)
    hist_hi, _ = np.histogram(seglen_hi, bins)
    np.add(cumul_hist_lo, hist_lo, out=cumul_hist_lo)
    np.add(cumul_hist_hi, hist_hi, out=cumul_hist_hi)

    # Plot
    if 0:
        # Timeseries
        plt.figure(fig_3)
        plt.cla()
        plt.plot(t, y)
        plt.plot(t_dfl, np.ones(t_dfl.size), "or")
        plt.plot(t_ufl, np.zeros(t_ufl.size), "or")
        plt.title(f"valve {i}")
        plt.xlabel(f"frame # + {t_offset}")
        plt.ylabel("state [0 - 1]")
        # plt.xlim(0, C.N_FRAMES)
        plt.xlim(4900, 5000)

    if 0:
        # Histogram
        plt.figure(fig_3)
        plt.cla()
        # plt.hist(seglen_hi, np.arange(0, 60), "b")
        # plt.hist(seglen_lo, np.arange(0, 60), "r")
        plt.step(bins[0:-1], hist_lo, "-k", where="mid")
        plt.step(bins[0:-1], hist_hi, "-r", where="mid")
        plt.title(f"valve {i}")
        plt.xlim(0, 50)

    # plt.show()
    # plt.show(block=False)
    # plt.pause(0.01)
    # plt.waitforbuttonpress()

# Cumulative pdf
pdf_lo = cumul_hist_lo / np.sum(cumul_hist_lo)
pdf_hi = cumul_hist_hi / np.sum(cumul_hist_hi)

plt.cla()
plt.step(bins[0:-1], pdf_lo, "-k", where="mid", label="off")
plt.step(bins[0:-1], pdf_hi, "-r", where="mid", label="on")
plt.title("Cumulative")
plt.xlabel("segment length")
plt.ylabel("PDF")
plt.xlim(0, 60)
plt.legend()
plt.grid()

if 1:
    plt.show(block=False)
    plt.pause(0.01)
    input("Press [Enter] to end.")
    plt.close("all")
