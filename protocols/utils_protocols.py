#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""utils_protocols.py

Utility functions for generating protocols.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "18-09-2024"
__version__ = "2.0"
# pylint: disable=invalid-name, missing-function-docstring

from time import perf_counter
from typing import Tuple

import numpy as np
from numba import prange
from tqdm import trange

from opensimplex_loops import looping_animated_2D_image
from utils_img_stack import (
    add_stack_B_to_A,
    binarize_stack_using_threshold,
    binarize_stack_using_newton,
)

import constants as C
import config_proto_opensimplex as CFG

# ------------------------------------------------------------------------------
#  generate_OpenSimplex_grayscale_img_stack
# ------------------------------------------------------------------------------


def generate_OpenSimplex_grayscale_img_stack() -> np.ndarray:
    """Generate OpenSimplex noise as specified in `config_proto_OpenSimplex.py`.

    Returns:
        img_stack_out (np.ndarray):
            2D image stack [time, y-pixel, x-pixel] containing float values
            within the range [-1, 1].
            Array shape: [N_frames, N_pixels, N_pixels]
    """

    # Range [-1, 1]
    img_stack_A = looping_animated_2D_image(
        N_frames=CFG.N_FRAMES,
        N_pixels_x=CFG.N_PIXELS,
        t_step=CFG.T_STEP_A,
        x_step=CFG.X_STEP_A,
        seed=CFG.SEED_A,
        dtype=np.float32,
    )
    print("")

    if CFG.SPATIAL_FEATURE_SIZE_B > 0:
        # Range [-1, 1]
        img_stack_B = looping_animated_2D_image(
            N_frames=CFG.N_FRAMES,
            N_pixels_x=CFG.N_PIXELS,
            t_step=CFG.T_STEP_B,
            x_step=CFG.X_STEP_B,
            seed=CFG.SEED_B,
            dtype=np.float32,
        )
        print("")

        add_stack_B_to_A(img_stack_A, img_stack_B)  # Range [-2, 2]
        np.divide(img_stack_A, 2, out=img_stack_A)  # Range [-1, 1]
        del img_stack_B

    return img_stack_A


# ------------------------------------------------------------------------------
#  binarize_img_stack
# ------------------------------------------------------------------------------


def binarize_img_stack(
    img_stack_in: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Binarize the passed grayscale image stack `img_stack_in` using a
    thresholding scheme as specified in `config_proto_OpenSimplex.py`.

    Returns: (Tuple)
        img_stack_BW (np.ndarray):
            2D image stack [time, y-pixel, x-pixel] containing 0 or 1 values.
            Array shape: [N_frames, N_pixels, N_pixels]

        alpha_BW (np.ndarray):
            Transparency of each `stack_BW` frame. Transparency is defined as
            the number of `1` elements over the total number of elements.
            Array shape: [N_frames]

        alpha_did_converge (np.ndarray):
            When the Newton solver is used, did it manage to converge to the
            given target transparency per frame?
            Array shape: [N_frames]
    """

    tick = perf_counter()
    img_stack_BW = np.zeros(img_stack_in.shape, dtype=bool)
    alpha_BW = np.zeros(img_stack_in.shape[0])
    alpha_BW_did_converge = np.zeros(CFG.N_FRAMES, dtype=bool)

    if CFG.BW_THRESHOLD is not None:
        # Constant BW threshold
        # Values above `BW_threshold` are set `True` (1), else `False` (0).
        print("Binarizing noise using a constant threshold...")
        binarize_stack_using_threshold(
            img_stack_in,
            CFG.BW_THRESHOLD,
            img_stack_BW,
            alpha_BW,
        )

    else:
        # Newton solver
        print("Binarizing noise solving for a target transparency...")
        binarize_stack_using_newton(
            img_stack_in,
            CFG.TARGET_TRANSPARENCY,
            img_stack_BW,
            alpha_BW,
            alpha_BW_did_converge,
        )

    print(f"done in {(perf_counter() - tick):.2f} s\n")
    return img_stack_BW, alpha_BW, alpha_BW_did_converge


# ------------------------------------------------------------------------------
#  compute_valves_stack
# ------------------------------------------------------------------------------


def compute_valves_stack(img_stack_BW: np.ndarray):
    """Compute the state of each valve based on the passed BW image stack
    `img_stack_BW`.

    Returns: (Tuple)
        valves_stack (np.ndarray):
            Stack containing the boolean states of all valves as 0's and 1's.
            Array shape: [N_frames, N_valves]

        alpha_valves (np.ndarray):
            Transparency of each `valves_stack` frame. Transparency is defined
            as the number of opened valves over the total number of valves.
            Array shape: [N_frames]
    """

    # NOTE: Use `int8` as type, not `bool` because we need `np.diff()` later.
    valves_stack = np.zeros([CFG.N_FRAMES, C.N_VALVES], dtype=np.int8)

    for frame in prange(CFG.N_FRAMES):  # pylint: disable=not-an-iterable
        valves_stack[frame, :] = (
            img_stack_BW[frame, CFG.valve2px_y, CFG.valve2px_x] == 1
        )

    # Valve transparency
    alpha_valves = valves_stack.sum(1) / C.N_VALVES

    return valves_stack, alpha_valves


# ------------------------------------------------------------------------------
#  export_protocol_to_disk
# ------------------------------------------------------------------------------


def export_protocol_to_disk(valves_stack: np.ndarray, export_path: str):
    """Exports the `valves_stack` to a text file on disk, formatted such that it
    can to be send over to the microcontroller.

    Args:
        valves_stack (np.ndarray):
            Stack containing the boolean states of all valves as 0's and 1's.
            Array shape: [N_frames, N_valves]

        export_path (str):
            Relative or absolute path including filename to write to.
    """
    print(f"Exporting protocol to disk as '{export_path}'...")
    tick = perf_counter()

    valves_stack = np.asarray(valves_stack, dtype=np.int8)
    N_frames, _ = valves_stack.shape

    with open(export_path, "w", encoding="utf-8") as f:
        # Write header info
        f.write("[HEADER]\n")
        f.write(CFG.create_header_string())

        # Write data
        f.write("[DATA]\n")
        for frame_idx in trange(N_frames):
            f.write(f"{CFG.DT_FRAME*1000:.0f}")  # Duration in msec
            for valve_idx, state in enumerate(valves_stack[frame_idx, :]):
                if state:
                    pcs_x = C.valve2pcs_x[valve_idx]
                    pcs_y = C.valve2pcs_y[valve_idx]
                    f.write(f"\t{pcs_x:d},{pcs_y:d}")
            f.write("\n")

    print(f"done in {perf_counter() - tick:.2f} s\n")
