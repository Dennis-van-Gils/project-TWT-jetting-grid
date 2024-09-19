#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plot the discrete PDF of 4D-OpenSimplex noise.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "09-09-2024"
# pylint: disable=missing-function-docstring

import numpy as np
from matplotlib import pyplot as plt
import opensimplex


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


# ------------------------------------------------------------------------------
#   4D-OpenSimplex noise PDF
# ------------------------------------------------------------------------------

N = 100
vicinity = 100
rng = np.random.default_rng(seed=0)
ix = (rng.random(N) - 0.5) * 2 * vicinity
iy = (rng.random(N) - 0.5) * 2 * vicinity
iz = (rng.random(N) - 0.5) * 2 * vicinity
iw = (rng.random(N) - 0.5) * 2 * vicinity

# Generate 4D OpenSimpex noise
noise_4D = opensimplex.noise4array(ix, iy, iz, iw)
N_points = noise_4D.size

# Histogram
bin_min = -1
bin_max = 1

pdf, bin_edges = np.histogram(
    noise_4D,
    range=(bin_min, bin_max),
    bins=101,
    density=True,
)

bin_width = bin_edges[1] - bin_edges[0]
bin_centers = bin_edges[:-1] + bin_width / 2

# Compare with Gaussian

mu = np.mean(noise_4D.flatten())
sigma = np.std(noise_4D.flatten())
noise_min = np.min(noise_4D)
noise_max = np.max(noise_4D)

print(f"Mean: {mu:.2e}")
print(f"Std : {sigma:.4f}")
print(f"Min : {noise_min:.4f}")
print(f"Max : {noise_max:.4f}")


def gaussian(x, mu, sigma):
    return (
        1.0
        / (np.sqrt(2.0 * np.pi) * sigma)
        * np.exp(-np.power((x - mu) / sigma, 2.0) / 2)
    )


x_gauss = np.linspace(-1, 1, 1001)
y_gauss = gaussian(x_gauss, mu=mu, sigma=sigma)

# ------------------------------------------------------------------------------
#   Plot
# ------------------------------------------------------------------------------

plt.figure(1)

plt.plot(bin_centers, pdf, "-r", label="4D-OpenSimplex")
plt.plot(x_gauss, y_gauss, "-k", label="normal dist.")

plt.xlim(-1, 1)
plt.ylim(bottom=0)

ylim_min, ylim_max = plt.ylim()
plt.plot((0, 0), (0, ylim_max), "-k", linewidth=0.5, label="_hidden")
plt.ylim(0, ylim_max)

plt.title(
    f"Sample size: {N}x{N}x{N}x{N} random points\n"
    f"over the domain [-{vicinity}, {vicinity}] along each axis"
)
plt.xlabel(r"$\mathrm{noise~value}$", usetex=True)
# plt.xlabel("noise value", fontsize=18)
plt.ylabel(r"$\mathrm{discrete~PDF}$", usetex=True)
# plt.ylabel("discrete PDF", fontsize=18)
plt.legend()

# NOTE:
#   > plt.xlabel(r"$\mathrm{noise~value}$", fontsize=20, usetex=True)
#   results in the same font height in effective millimeters as:
#   > plt.xlabel("noise value", fontsize=18)

if False:
    plt.savefig("PDF_4D_OpenSimplex.pdf")

plt.show()
