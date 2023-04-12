#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JettingGrid_qdev.py

Manages multi-threaded communication with the Jetting Grid Arduino
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "12-04-2023"
__version__ = "1.0"

import numpy as np

from dvg_devices.Arduino_protocol_serial import Arduino
from dvg_qdeviceio import QDeviceIO


class JettingGrid_qdev(QDeviceIO):
    class State(object):
        def __init__(self):
            # Actual readings of the Arduino
            self.time = np.nan  # [s]
            self.protocol_pos = 0
            self.P_1_mA = np.nan  # [mA]
            self.P_2_mA = np.nan  # [mA]
            self.P_3_mA = np.nan  # [mA]
            self.P_4_mA = np.nan  # [mA]
            self.P_1_bar = np.nan  # [bar]
            self.P_2_bar = np.nan  # [bar]
            self.P_3_bar = np.nan  # [bar]
            self.P_4_bar = np.nan  # [bar]

            # Interaction flags to communicate with the Xylem jetting pump that
            # is running inside of another thread
            self.waiting_for_pump_standstill_to_stop_protocol = False

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

    def send_play_protocol(self) -> bool:
        return self.send(self.dev.write, "play")

    def send_stop_protocol(self) -> bool:
        return self.send(self.dev.write, "stop")

    def send_pause_protocol(self) -> bool:
        return self.send(self.dev.write, "pause")
