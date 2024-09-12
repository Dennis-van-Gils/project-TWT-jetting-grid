#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plot a 2D slice out of 4D-OpenSimplex noise.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "10-09-2024"
# pylint: disable=missing-function-docstring

import numpy as np
from matplotlib import pyplot as plt

import opensimplex
from opensimplex.internals import _init, _noise4
from numba import njit, prange

FONTSIZE_DEFAULT = 12
FONTSIZE_AXESLABELS = 20
FONTSIZE_LEGEND = 12
FONTSIZE_TICKLABELS = 12
FONTSIZE_TITLE = 12

plt.rcParams.update(
    {
        "text.usetex": False,  # We'll use 'usetex=True' on a per label basis.
        "pdf.fonttype": 42,  # 42: Embed fonts
        #
        "font.size": FONTSIZE_DEFAULT,
        "font.family": "sans-serif",
        "font.sans-serif": "Arial",
        #
        "figure.subplot.top": 0.9,
        "figure.subplot.bottom": 0.15,
        "figure.subplot.left": 0.15,
        "figure.subplot.right": 0.950,
        #
        "axes.labelsize": FONTSIZE_AXESLABELS,
        "axes.titlesize": FONTSIZE_TITLE,
        #
        "xtick.labelsize": FONTSIZE_TICKLABELS,
        "xtick.major.size": 5,
        "xtick.minor.size": 3,
        "ytick.labelsize": FONTSIZE_TICKLABELS,
        "ytick.major.size": 5,
        "ytick.minor.size": 3,
        #
        "legend.fancybox": False,
        "legend.framealpha": 1,
        "legend.edgecolor": "black",
        "legend.fontsize": FONTSIZE_LEGEND,
    }
)


@njit(
    cache=True,
    parallel=True,
    nogil=True,
)
def noise_numba(
    _ix: np.ndarray, _iy: np.ndarray, _perm: np.ndarray
) -> np.ndarray:
    """Return a 2D-slice of 4D-OpenSimplex noise. Numba accelerated parallel
    computation."""
    N_ix = _ix.size
    N_iy = _iy.size
    noise = np.empty((N_iy, N_ix))
    for _idx_y in prange(N_iy):
        for _idx_x in prange(N_ix):
            noise[_idx_y, _idx_x] = _noise4(
                _ix[_idx_x], _iy[_idx_y], 0, 0, _perm
            )

    return noise


if __name__ == "__main__":
    vicinity = 4
    step = 0.01
    ix = np.arange(-vicinity, vicinity, step)
    iy = np.arange(-vicinity, vicinity, step)

    method = 2
    if method == 0:
        # Correct, but very memory hungry because we construct NxNxNxN
        iz = np.zeros(ix.size)
        iw = np.zeros(ix.size)
        noise_4D = opensimplex.noise4array(ix, iy, iz, iw)
        slice_2D = noise_4D[0, 0, :, :]

    elif method == 1:
        # Identical output, but more memory efficient this time although still slow
        perm, _ = _init(3)
        slice_2D = np.empty((iy.size, ix.size))

        for idx_y, val_y in enumerate(iy):
            for idx_x, val_x in enumerate(ix):
                slice_2D[idx_y, idx_x] = _noise4(val_x, val_y, 0, 0, perm)

    else:
        # Identical output, fast and efficient because we compile to C using numba
        perm, _ = _init(3)
        slice_2D = noise_numba(ix, iy, perm)

    print(f"(min, max) = ({np.min(slice_2D):.3f}, {np.max(slice_2D):.3f})")

    plt.imshow(
        slice_2D,
        cmap="gray",
        vmin=-0.7,
        vmax=0.7,
        interpolation="none",
        origin="lower",
        extent=(-vicinity, vicinity, -vicinity, vicinity),
    )
    plt.colorbar(label="noise value")
    plt.xlabel(r"$x$", usetex=True)
    plt.ylabel(r"$y$", usetex=True)
    plt.title("2D slice out of 4D-OpenSimplex noise\nin the plane (x, y, 0, 0)")

    plt.savefig("slice_2D_of_4D_OpenSimplex.pdf")
    plt.show()
