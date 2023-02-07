#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Dennis van Gils"
# pylint: disable=invalid-name

import numpy as np
from matplotlib import pyplot as plt

from utils_matplotlib import move_figure
from utils_valves_stack import adjust_valve_times, valve_on_off_PDFs
import config_proto_OpenSimplex as CFG

# ------------------------------------------------------------------------------
#  Valve ON/OFF duration PDFs
# ------------------------------------------------------------------------------
MIN_VALVE_DURATION = 5

# Load data from disk
valves_stack_in = np.asarray(
    np.load(CFG.EXPORT_PATH_NO_EXT + "_valves_stack.npy"), dtype=np.int8
)

# Adjust valve times
valves_stack_out = adjust_valve_times(valves_stack_in, MIN_VALVE_DURATION)

# Calculate PDFs
bins = np.arange(0, CFG.N_FRAMES)
pdf_off_1, pdf_on_1 = valve_on_off_PDFs(valves_stack_in, bins)
pdf_off_2, pdf_on_2 = valve_on_off_PDFs(valves_stack_out, bins)

# Plot
fig_4, axs = plt.subplots(2)
fig_4.set_tight_layout(True)
move_figure(fig_4, 200, 0)

axs[0].set_title("valve OFF")
axs[0].step(bins[0:-1], pdf_off_1, "-r", where="mid", label="original")
axs[0].step(bins[0:-1], pdf_off_2, "-k", where="mid", label="adjusted")

axs[1].set_title("valve ON")
axs[1].step(bins[0:-1], pdf_on_1, "-r", where="mid", label="original")
axs[1].step(bins[0:-1], pdf_on_2, "-k", where="mid", label="adjusted")

for ax in axs:
    ax.set_xlabel("duration")
    ax.set_ylabel("PDF")
    ax.set_xlim(0, 60)
    ax.legend()
    ax.grid()

plt.show()
# plt.show(block=False)
# plt.pause(0.01)
# input("Press [Enter] to end.")
# plt.close("all")
