#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""calculate_coherent_scales_proto_opensimplex.py

TODO: NOT FINISHED. No meaningful results yet.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "25-08-2023"
__version__ = "1.0"
# pylint: disable=invalid-name, missing-function-docstring

import sys

import numpy as np
import scipy.signal
from matplotlib import pyplot as plt

from utils_protocols import (
    generate_OpenSimplex_grayscale_img_stack,
    binarize_img_stack,
)
import config_proto_opensimplex as CFG
from dvg_fftw_autocorrelate2d import FFTW_Autocorrelator_2D
from dvg_fftw_convolve2d import FFTW_Convolver_Full2D

# Flags useful for developing. Leave both set to False for normal operation.
LOAD_FROM_CACHE = True
SAVE_TO_CACHE = False

# ------------------------------------------------------------------------------
#  Check validity of user configurable parameters
# ------------------------------------------------------------------------------

if (CFG.BW_THRESHOLD is not None and CFG.TARGET_TRANSPARENCY is not None) or (
    CFG.BW_THRESHOLD is None and CFG.TARGET_TRANSPARENCY is None
):
    print(
        "ERROR: Invalid configuration in `config_proto_opensimplex.py`.\n"
        "Either specify `BW_THRESHOLD` or specify `TARGET_TRANSPARENCY`."
    )
    sys.exit(0)

# ------------------------------------------------------------------------------
#  Generate OpenSimplex protocol
# ------------------------------------------------------------------------------

if not LOAD_FROM_CACHE:
    # Generate OpenSimplex grayscale noise
    img_stack_gray = generate_OpenSimplex_grayscale_img_stack()

    # Binarize OpenSimplex noise
    (
        img_stack_BW,
        alpha_BW,
        alpha_BW_did_converge,
    ) = binarize_img_stack(img_stack_gray)

    if SAVE_TO_CACHE:
        print("Saving cache to disk...")
        np.savez(
            "cache.npz",
            img_stack_BW=img_stack_BW,
            img_stack_gray=img_stack_gray,
        )
        print(f"done.\n")

else:
    # Developer: Retrieving data straight from the cache file on disk
    print("Reading cache from disk...")
    with np.load("cache.npz", allow_pickle=False) as cache:
        img_stack_BW = cache["img_stack_BW"]
        img_stack_gray = cache["img_stack_gray"]
    print(f"done.")

# ------------------------------------------------------------------------------
#  Calculate coherent scales via autocorrelation
# ------------------------------------------------------------------------------
stack = img_stack_gray

# fftw_convolver2d = FFTW_Convolver_Full2D(stack[0].shape, stack[0].shape)
fftw_autocorrelator2d = FFTW_Autocorrelator_2D(stack[0].shape)

N_frames = stack.shape[0]
for frame_idx in range(N_frames):
    img = stack[frame_idx]  # .astype(float)
    # Cxx = fftw_convolver2d.convolve(img, img)
    Cxx = fftw_autocorrelator2d.autocorrelate(img)

    # print(f"{np.min(Cxx):.3f}, {np.max(Cxx):.3f}")

    # Find maximum peak
    iMaxCxx = int(np.argmax(Cxx))
    peak_x = iMaxCxx % Cxx.shape[1]  # unravel index
    peak_y = iMaxCxx // Cxx.shape[0]  # unravel index

    # Plot
    if not (plt.fignum_exists(1)):  # type: ignore
        fig, axs = plt.subplots(nrows=1, ncols=2)  # type: ignore

        h_img = axs[0].imshow(  # type: ignore
            img,
            cmap="gray",
            interpolation="none",
            vmin=0.0,
            vmax=1.0,
        )

        h_Cxx = axs[1].imshow(  # type: ignore
            Cxx,
            cmap="gray",
            interpolation="none",
            # vmin=0.2,
            # vmax=0.3,
        )
        (h_peak,) = axs[1].plot([peak_x], [peak_y], "xr")  # type: ignore

        h_title = plt.title(f"{frame_idx} of {N_frames}")  # type: ignore
    else:
        h_img.set_data(img)  # type: ignore
        h_Cxx.set_data(Cxx)  # type: ignore
        h_peak.set_data([peak_x], [peak_y])  # type: ignore
        h_title.set_text(f"{frame_idx} of {N_frames}")  # type: ignore

    # plt.show()
    # plt.show(block=False)
    plt.draw()
    plt.pause(0.1)
