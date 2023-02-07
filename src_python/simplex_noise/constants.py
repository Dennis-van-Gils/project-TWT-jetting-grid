#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration constants for the generation of a turbulent jetting protocol
using OpenSimplex noise.
"""
# pylint: disable=pointless-string-statement
# fmt: off
__author__ = "Dennis van Gils"

"""
Protocol coordinate system (PCS):
  The jetting nozzles are laid out in a square grid, aka the protocol coordinate
  system.

  ●: Indicates a valve & nozzle
  -: Indicates no nozzle & valve exists

      -7 -6 -5 -4 -3 -2 -1  0  1  2  3  4  5  6  7
     ┌─────────────────────────────────────────────┐
   7 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
   6 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
   5 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
   4 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
   3 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
   2 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
   1 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
   0 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
  -1 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
  -2 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
  -3 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
  -4 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
  -5 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
  -6 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
  -7 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
     └─────────────────────────────────────────────┘
"""

import numpy as _np

# Constants taken from `src_mcu\src\constants.h`
# ----------------------------------------------
# The PCS spans (-7, -7) to (7, 7) where (0, 0) is the center of the grid.
# Physical valves are numbered 1 to 112, with 0 indicating 'no valve'.
PCS_X_MIN = -7  # Minimum x-axis coordinate of the PCS
PCS_X_MAX = 7   # Maximum x-axis coordinate of the PCS
NUMEL_PCS_AXIS = PCS_X_MAX - PCS_X_MIN + 1
N_VALVES = int(_np.floor(NUMEL_PCS_AXIS * NUMEL_PCS_AXIS / 2))  # == 112

# General constants
# -----------------
# Pixel distance between the integer PCS coordinates.
# Too large -> memory intense. Too small -> poor quality.
# 32 is a good value. Leave it.
PCS_PIXEL_DIST = 32

PLOT_TO_SCREEN = 1        # [0] Save plots to disk, [1] Show on screen
SHOW_NOISE_IN_PLOT = 1    # [0] Only show valves,   [1] Show noise as well
SHOW_NOISE_AS_GRAY = 0    # Show noise as [0] BW,   [1] Grayscale

# Protocol parameters
# -------------------
N_FRAMES = 5000
N_PIXELS = PCS_PIXEL_DIST * (NUMEL_PCS_AXIS + 1)

# Threshold level to convert grayscale noise to BW. Can also get
# reinterpreted as a transparency fraction [0-1] to solve for.
BW_THRESHOLD = 0.5

# Interpret `BW_THRESHOLD` as a wanted transparency per frame to solve for?
# It is a very good idea to leave this on as it minimizes the fluctuation of
# the resulting valve transparency over each frame.
TUNE_TRANSPARENCY = 1

# Noise feature size [arb. unit]
FEATURE_SIZE_A = 50   # Try 50
FEATURE_SIZE_B = 100  # Try 100. 0 indicates to not use stack B.

# Time step [arb. unit]
T_STEP_A = 0.1
T_STEP_B = 0.1

# Noise seeds
SEED_A = 1
SEED_B = 13

# Minimum valve on/off duration
MIN_VALVE_DURATION = 5

# ------------------------------------------------------------------------------
#  Valve transformations
# ------------------------------------------------------------------------------
# NOTE: The valve index of below arrays does /not/ indicate the valve number as
# laid out in the lab, but instead is simply linearly increasing.

# Create a map holding the pixel locations inside the noise image corresponding
# to each valve location
_pxs = _np.arange(
    PCS_PIXEL_DIST - 1, N_PIXELS - (PCS_PIXEL_DIST - 1), PCS_PIXEL_DIST
)
_grid_x, _grid_y = _np.meshgrid(_pxs, _pxs)  # shape: (15, 15), (15, 15)
# `grid_x` and `grid_y` map /all/ integer PCS coordinates. We only need the
# locations that actually correspond to a valve.
valve2px_x = _np.reshape(_grid_x, -1)[1::2]  # shape: (112,)
valve2px_y = _np.reshape(_grid_y, -1)[1::2]  # shape: (112,)

# Create a map holding the PCS coordinates of each valve
_coords = _np.arange(PCS_X_MIN, PCS_X_MAX + 1)
_grid_x, _grid_y = _np.meshgrid(_coords, _coords)  # shape: (15, 15), (15, 15)
# `grid_x` and `grid_y` map /all/ integer PCS coordinates. We only need the
# locations that actually correspond to a valve.
valve2pcs_x = _np.reshape(_grid_x, -1)[1::2]  # shape: (112,)
valve2pcs_y = _np.reshape(_grid_y, -1)[1::2]  # shape: (112,)

# Tidy up the namespace
del _pxs, _coords, _grid_x, _grid_y
del _np
