#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utility functions that operate on a `valves_stack`.
"""
__author__ = "Dennis van Gils"
# pylint: disable=invalid-name, missing-function-docstring

from time import perf_counter

import numpy as np
from tqdm import trange

# from numba import prange

import constants as C

# Constants
filename = "proto_1.txt"
DT = 0.1  # [s] Fixed time interval of each frame

# Load valves stack
valves_stack = np.asarray(np.load("proto_valves_stack_out.npy"), dtype=np.int8)

print("Saving protocol to disk...")
tick = perf_counter()

N_frames, N_valves = valves_stack.shape

with open(filename, "w", encoding="utf-8") as f:
    # Write header info
    f.write("[HEADER]\n")
    f.write(f"N_frames: {N_frames}\n")
    f.write(f"N_valves: {N_valves}\n")

    # Write data
    timestamp = 0
    f.write("[DATA]\n")
    for frame_idx in trange(N_frames):
        f.write(f"{timestamp:.1f}")
        timestamp += DT
        for valve_idx, state in enumerate(valves_stack[frame_idx, :]):
            if state:
                pcs_x = C.valve2pcs_x[valve_idx]
                pcs_y = C.valve2pcs_y[valve_idx]
                f.write(f"\t{pcs_x:d},{pcs_y:d}")
        f.write("\n")

    print(f"done in {perf_counter() - tick:.2f} s\n")
