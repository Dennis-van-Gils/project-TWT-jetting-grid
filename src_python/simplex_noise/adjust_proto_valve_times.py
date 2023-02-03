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

for i in np.arange(C.N_VALVES):
    # Load timeseries of valve
    y = valves_stack[:, i]

    # The timeseries are a closed loop, so we do a trick.
    # We shift all timeseries to let them start at the first downflank.
    # -----------------------------------------------------------------
    y = np.concatenate((y, y))
    t_offset = find_first_downflank(y)
    y = y[t_offset : t_offset + C.N_FRAMES]

    # Calculate the segment lengths of valve on/off states
    # ----------------------------------------------------
    # dfl: downflank
    # ufl: upflank
    t_dfl = np.where(np.diff(y) == -1)[0]
    t_ufl = np.where(np.diff(y) == 1)[0]
    print(
        f"{t_offset:4d}  {t_dfl.size:4d}  {t_ufl.size:4d}  "
        f"{t_dfl.size==t_ufl.size}"
    )

    t = np.arange(0, C.N_FRAMES)

    plt.cla()
    plt.plot(t, y)
    plt.plot(t_dfl, np.ones(t_dfl.size), "or")
    plt.plot(t_ufl, np.zeros(t_ufl.size), "or")
    # plt.xlim(0, C.N_FRAMES)
    plt.xlim(0, 100)
    plt.title(f"valve {i}")
    plt.xlabel(f"frame # + {t_offset}")
    plt.ylabel("state [0 - 1]")

    plt.show(block=False)
    plt.pause(0.25)


if 1:
    plt.show(block=False)
    plt.pause(0.001)
    input("Press [Enter] to end.")
    plt.close("all")
