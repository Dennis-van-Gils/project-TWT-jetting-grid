#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TODO: IN PROGRESS. UNFUGLIFY.
"""
__author__ = "Dennis van Gils"
# pylint: disable=invalid-name, missing-function-docstring

import os
from time import perf_counter

import numpy as np
from tqdm import trange

import constants as C
import config_proto_OpenSimplex as CFG

# Constants
filename = os.path.join(CFG.EXPORT_SUBFOLDER, "proto_example.txt")

# Load valves stack
valves_stack = np.asarray(
    np.load(
        os.path.join(
            CFG.EXPORT_SUBFOLDER, "proto_example_valves_stack_adjusted.npy"
        )
    ),
    dtype=np.int8,
)

print("Saving protocol to disk...")
tick = perf_counter()

N_frames, N_valves = valves_stack.shape

with open(filename, "w", encoding="utf-8") as f:
    # Write header info
    f.write("[HEADER]\n")
    f.write(CFG.create_header_string())

    # Write data
    timestamp = 0
    f.write("[DATA]\n")
    for frame_idx in trange(N_frames):
        f.write(f"{timestamp:.1f}")
        timestamp += CFG.DT_FRAME
        for valve_idx, state in enumerate(valves_stack[frame_idx, :]):
            if state:
                pcs_x = C.valve2pcs_x[valve_idx]
                pcs_y = C.valve2pcs_y[valve_idx]
                f.write(f"\t{pcs_x:d},{pcs_y:d}")
        f.write("\n")

    print(f"done in {perf_counter() - tick:.2f} s\n")
