#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utility functions for generating protocols.
"""
__author__ = "Dennis van Gils"
# pylint: disable=invalid-name, missing-function-docstring

from time import perf_counter
from typing import Tuple

import numpy as np
from numba import prange
from tqdm import trange

from opensimplex_loops import looping_animated_2D_image
from utils_img_stack import (
    add_stack_B_to_A,
    rescale_stack,
    binarize_stack,
)

import constants as C
import config_proto_opensimplex as CFG

# ------------------------------------------------------------------------------
#  generate_protocol_arrays_OpenSimplex
# ------------------------------------------------------------------------------


def generate_protocol_arrays_OpenSimplex() -> Tuple[
    np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray
]:
    """Generate 'protocol' arrays based on OpenSimplex noise as given by the
    user-configurable parameters taken from `config_proto_OpenSimplex.py`.

    Transparency is defined as the number of `True / 1 / valve on` elements over
    the total number of elements.

    Returns: (Tuple)
        valves_stack (np.ndarray):
            Stack containing the boolean states of all valves as 0's and 1's.
            Array shape: [N_frames, N_valves]

        img_stack_noise (np.ndarray):
            2D image stack [time, y-pixel, x-pixel] containing float values.
            This is the underlying OpenSimplex noise data for `valves_stack`
            before binarization.
            Array shape: [N_frames, N_pixels, N_pixels]

        img_stack_noise_BW (np.ndarray):
            2D image stack [time, y-pixel, x-pixel] containing 0 or 1 values.
            This is the underlying OpenSimplex noise data for `valves_stack`
            after binarization.
            Array shape: [N_frames, N_pixels, N_pixels]

        alpha_noise (np.ndarray):
            Transparency of each `img_stack_noise_BW` frame.
            Array shape: [N_frames]

        alpha_valves (np.ndarray):
            Transparency of each `valves_stack` frame.
            Array shape: [N_frames]
    """

    # Generate noise image stacks
    # ---------------------------

    # Pixel value range between [-1, 1]
    img_stack_A = looping_animated_2D_image(
        N_frames=CFG.N_FRAMES,
        N_pixels_x=CFG.N_PIXELS,
        t_step=CFG.T_STEP_A,
        x_step=CFG.X_STEP_A,
        seed=CFG.SEED_A,
        dtype=np.float32,
    )
    print("")

    if CFG.FEATURE_SIZE_B > 0:
        # Pixel value range between [-1, 1]
        img_stack_B = looping_animated_2D_image(
            N_frames=CFG.N_FRAMES,
            N_pixels_x=CFG.N_PIXELS,
            t_step=CFG.T_STEP_B,
            x_step=CFG.X_STEP_B,
            seed=CFG.SEED_B,
            dtype=np.float32,
        )
        print("")

        # Pixel value range between [-2, 2]
        add_stack_B_to_A(img_stack_A, img_stack_B)
        del img_stack_B

    # Rescale and offset all images in the stack to lie within the range [0, 1].
    # Leave `symmetrically=True` to prevent biasing the pixel intensity
    # distribution towards 0 or 1.
    rescale_stack(img_stack_A, symmetrically=True)

    # Transform grayscale noise into binary BW map, optionally solving for a
    # desired transparency level.
    img_stack_BW, alpha_noise = binarize_stack(
        img_stack_A, CFG.BW_THRESHOLD, CFG.TUNE_TRANSPARENCY
    )

    # Generate valves stack
    # ---------------------

    # Determine the state of each valve based on the BW noise image stack
    # NOTE: Use `int8` as type, not `bool` because we need `np.diff()` later.
    valves_stack = np.zeros([CFG.N_FRAMES, C.N_VALVES], dtype=np.int8)

    for frame in prange(CFG.N_FRAMES):  # pylint: disable=not-an-iterable
        valves_stack[frame, :] = (
            img_stack_BW[frame, CFG.valve2px_y, CFG.valve2px_x] == 1
        )

    # Calculate the valve transparency
    alpha_valves = valves_stack.sum(1) / C.N_VALVES

    return valves_stack, img_stack_A, img_stack_BW, alpha_noise, alpha_valves


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
