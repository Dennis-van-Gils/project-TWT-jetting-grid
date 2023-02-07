#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""User configuration parameters for the generation of a jetting protocol using
OpenSimplex noise.

Two different sets of OpenSimplex noise can be mixed together: set A and set B.
You could specify a larger typical length scale for set B than for set A,
as specified by `FEATURE_SIZE`. Likewise the same for the typical time scale as
specified by `T_STEP`.

If `FEATURE_SIZE_B` is set to 0, set B will be completely ignored and no mixing
will take place.

These settings will get stored inside the header section of the generated
protocol textfile.
"""

# Filename without extension for exporting the generated protocol files to disk.
# Leaving it blank will auto-generate a name like "proto_###".
EXPORT_FILENAME = "proto_001"
EXPORT_SUBFOLDER = "protocols"

# Number of frames (i.e. protocol lines) to generate
N_FRAMES = 5000

# Threshold level to convert [0-1]-grayscale OpenSimplex noise to black and
# white (BW). Can also get reinterpreted as a transparency fraction [0-1] to
# solve for, see `TUNE_TRANSPARENCY`.
BW_THRESHOLD = 0.5

# Interpret `BW_THRESHOLD` as a wanted transparency per frame to solve for?
# It is a very good idea to leave this on as it minimizes the fluctuation of
# the resulting valve transparency over each frame.
TUNE_TRANSPARENCY = 1

# OpenSimplex noise feature size [arb. unit, try ~ 50]
FEATURE_SIZE_A = 50
FEATURE_SIZE_B = 100

# Time step [arb. unit, try ~ 0.1]
T_STEP_A = 0.1
T_STEP_B = 0.1

# Noise seeds
SEED_A = 1
SEED_B = 13

# Minimum valve on/off duration [number of frames]
MIN_VALVE_DURATION = 5


# ------------------------------------------------------------------------------
#  End of user-configurable parameters
#  Do not edit the code below
# ------------------------------------------------------------------------------
__author__ = "Dennis van Gils"

import numpy as _np
import constants as C

# Pixel distance between the integer PCS coordinates.
# Too large -> memory intense. Too small -> poor quality.
# 32 is a good value. Leave it.
PCS_PIXEL_DIST = 32
N_PIXELS = PCS_PIXEL_DIST * (C.NUMEL_PCS_AXIS + 1)

# Derived
X_STEP_A = _np.divide(1, FEATURE_SIZE_A * PCS_PIXEL_DIST / 32)
if FEATURE_SIZE_B != 0:
    X_STEP_B = _np.divide(1, FEATURE_SIZE_B * PCS_PIXEL_DIST / 32)
else:
    X_STEP_B = 0

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

# Tidy up the namespace
del _pxs, _grid_x, _grid_y
del _np
