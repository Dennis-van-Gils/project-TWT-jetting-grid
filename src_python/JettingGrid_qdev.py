#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JettingGrid_qdev.py

Manages multi-threaded communication with the Arduino
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "17-03-2023"
__version__ = "1.0"

import numpy as np

from dvg_devices.Arduino_protocol_serial import Arduino
from dvg_qdeviceio import QDeviceIO


class JettingGrid_qdev(QDeviceIO):
    class State(object):
        def __init__(self):
            # Actual readings of the Arduino
            self.time = np.nan  # [s]
            self.P_1_mA = np.nan  # [mA]
            self.P_2_mA = np.nan  # [mA]
            self.P_3_mA = np.nan  # [mA]
            self.P_4_mA = np.nan  # [mA]
            self.P_1_bar = np.nan  # [bar]
            self.P_2_bar = np.nan  # [bar]
            self.P_3_bar = np.nan  # [bar]
            self.P_4_bar = np.nan  # [bar]

    # --------------------------------------------------------------------------
    #   JettingGrid_qdev
    # --------------------------------------------------------------------------

    def __init__(
        self,
        dev: Arduino,
        DAQ_function=None,
        DAQ_interval_ms=100,
        debug=False,
        **kwargs,
    ):
        super().__init__(dev, **kwargs)  # Pass kwargs onto QtCore.QObject()

        self.state = self.State()

        self.create_worker_DAQ(
            DAQ_function=DAQ_function,
            DAQ_interval_ms=DAQ_interval_ms,
            critical_not_alive_count=3,
            debug=debug,
        )
        self.create_worker_jobs(debug=debug)

    # --------------------------------------------------------------------------
    #   Arduino communication functions
    # --------------------------------------------------------------------------
