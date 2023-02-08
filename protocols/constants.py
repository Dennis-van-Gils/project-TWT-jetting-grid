#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration constants of the jetting grid of the Twente Water Tunnel.

Protocol coordinate system (PCS):
  The jetting nozzles are laid out in a square grid, aka the protocol coordinate
  system.

  The PCS spans (-7, -7) to (7, 7) where (0, 0) is the center of the grid.

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
__author__ = "Dennis van Gils"

import numpy as _np

# ------------------------------------------------------------------------------
#  Constants taken from `src_mcu\src\constants.h`
# ------------------------------------------------------------------------------

PCS_X_MIN = -7  # Minimum x-axis coordinate of the PCS
PCS_X_MAX = 7  # Maximum x-axis coordinate of the PCS
NUMEL_PCS_AXIS = PCS_X_MAX - PCS_X_MIN + 1
N_VALVES = int(_np.floor(NUMEL_PCS_AXIS * NUMEL_PCS_AXIS / 2))  # == 112

# ------------------------------------------------------------------------------
#  Valve transformations
# ------------------------------------------------------------------------------
# NOTE: The valve index of below arrays does /not/ indicate the valve number as
# laid out in the lab, but instead is simply linearly increasing.

# Create a map holding the PCS coordinates of each valve
_coords = _np.arange(PCS_X_MIN, PCS_X_MAX + 1)
_grid_x, _grid_y = _np.meshgrid(_coords, _coords)  # shape: (15, 15), (15, 15)
# `grid_x` and `grid_y` map /all/ integer PCS coordinates. We only need the
# locations that actually correspond to a valve.
valve2pcs_x = _np.reshape(_grid_x, -1)[1::2]  # shape: (112,)
valve2pcs_y = _np.reshape(_grid_y, -1)[1::2]  # shape: (112,)

# Tidy up the namespace
del _coords, _grid_x, _grid_y
del _np
