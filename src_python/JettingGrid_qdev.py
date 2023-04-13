#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JettingGrid_qdev.py

Manages multi-threaded communication with the Jetting Grid Arduino
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "13-04-2023"
__version__ = "1.0"

import os
import sys

# Mechanism to support both PyQt and PySide
# -----------------------------------------

PYQT5 = "PyQt5"
PYQT6 = "PyQt6"
PYSIDE2 = "PySide2"
PYSIDE6 = "PySide6"
QT_LIB_ORDER = [PYQT5, PYSIDE2, PYSIDE6, PYQT6]
QT_LIB = None

if QT_LIB is None:
    for lib in QT_LIB_ORDER:
        if lib in sys.modules:
            QT_LIB = lib
            break

if QT_LIB is None:
    for lib in QT_LIB_ORDER:
        try:
            __import__(lib)
            QT_LIB = lib
            break
        except ImportError:
            pass

if QT_LIB is None:
    this_file = __file__.split(os.sep)[-1]
    raise ImportError(
        f"{this_file} requires PyQt5, PyQt6, PySide2 or PySide6; "
        "none of these packages could be imported."
    )

# fmt: off
# pylint: disable=import-error, no-name-in-module
if QT_LIB == PYQT5:
    from PyQt5.QtCore import pyqtSignal as Signal          # type: ignore
    from PyQt5.QtCore import pyqtSlot as Slot              # type: ignore
elif QT_LIB == PYQT6:
    from PyQt6.QtCore import pyqtSignal as Signal          # type: ignore
    from PyQt6.QtCore import pyqtSlot as Slot              # type: ignore
elif QT_LIB == PYSIDE2:
    from PySide2.QtCore import Signal, Slot                # type: ignore
elif QT_LIB == PYSIDE6:
    from PySide6.QtCore import Signal, Slot                # type: ignore
# pylint: enable=import-error, no-name-in-module
# fmt: on

# \end[Mechanism to support both PyQt and PySide]
# -----------------------------------------------

from JettingGrid_Arduino import JettingGrid_Arduino
from dvg_debug_functions import print_fancy_traceback as pft
from dvg_qdeviceio import QDeviceIO

# ------------------------------------------------------------------------------
#   JettingGrid_qdev
# ------------------------------------------------------------------------------


class JettingGrid_qdev(QDeviceIO):
    signal_GUI_needs_update = Signal()

    def __init__(
        self,
        dev: JettingGrid_Arduino,
        DAQ_function=None,
        DAQ_interval_ms=100,
        debug=False,
        **kwargs,
    ):
        super().__init__(dev, **kwargs)  # Pass kwargs onto QtCore.QObject()
        self.dev: JettingGrid_Arduino

        self.create_worker_DAQ(
            DAQ_function=DAQ_function,
            DAQ_interval_ms=DAQ_interval_ms,
            critical_not_alive_count=3,
            debug=debug,
        )
        self.create_worker_jobs(jobs_function=self.jobs_function, debug=debug)

        # Interaction flags to communicate with the Xylem jetting pump that is
        # running inside of another thread
        self.waiting_for_pump_standstill_to_stop_protocol = False

    # --------------------------------------------------------------------------
    #   jobs_function
    # --------------------------------------------------------------------------

    def jobs_function(self, func, args):
        if func == "signal_GUI_needs_update":
            # Special instruction
            self.signal_GUI_needs_update.emit()
        else:
            # Default job processing:
            # Send I/O operation to the device
            try:
                func(*args)
            except Exception as err:
                pft(err)

    # --------------------------------------------------------------------------
    #   Arduino communication functions
    # --------------------------------------------------------------------------

    @Slot()
    def pump_has_reached_standstill(self):
        """We got a confirmation signal that the pump has reached standstill,
        so now we can safely send the `stop protocol` command and close all
        valves."""
        if self.waiting_for_pump_standstill_to_stop_protocol:
            self.waiting_for_pump_standstill_to_stop_protocol = False
            self.send_stop_protocol()

    @Slot()
    def send_play_protocol(self):
        """Play the protocol and automatically actuate valves over time."""
        self.send(self.dev.play_protocol)

    @Slot()
    def send_stop_protocol(self):
        """Stop the protocol and immediately close all valves.

        WARNING: This method is ignorant of whether the jetting pump is running
        or not. Closing all valves suddenly while the pump is running can damage
        the system.
        """
        # NOTE: It is actually redundant to trigger a GUI update to update the
        # protocol position textbox at the moment of 'stop'. DAQ_worker already
        # triggers GUI updates of this control (and others) at 10 Hz. Still, we
        # keep it as a good practice. So, in theory, below block could be
        # replaced by a single instruction: self.send(self.dev.stop_protocol).
        self.add_to_jobs_queue(self.dev.stop_protocol)
        self.add_to_jobs_queue("signal_GUI_needs_update")
        self.process_jobs_queue()

    @Slot()
    def send_pause_protocol(self):
        """Pause the protocol keeping the last actuated states of the valves."""
        self.add_to_jobs_queue(self.dev.pause_protocol)
        self.add_to_jobs_queue("signal_GUI_needs_update")
        self.process_jobs_queue()

    @Slot()
    def send_rewind_protocol(self):
        """Rewind the protocol and immediately actuate valves."""
        self.add_to_jobs_queue(self.dev.rewind_protocol)
        self.add_to_jobs_queue("signal_GUI_needs_update")
        self.process_jobs_queue()

    @Slot()
    def send_prevline_protocol(self):
        """Go to the previous line of the protocol and immediately actuate
        valves."""
        self.add_to_jobs_queue(self.dev.prevline_protocol)
        self.add_to_jobs_queue("signal_GUI_needs_update")
        self.process_jobs_queue()

    @Slot()
    def send_nextline_protocol(self):
        """Go to the next line of the protocol and immediately actuate valves."""
        self.add_to_jobs_queue(self.dev.nextline_protocol)
        self.add_to_jobs_queue("signal_GUI_needs_update")
        self.process_jobs_queue()

    @Slot(int)
    def send_gotoline_protocol(self, line_no: int):
        """Go to the given line number of the protocol and immediately actuate
        valves."""
        self.add_to_jobs_queue(self.dev.gotoline_protocol, line_no)
        self.add_to_jobs_queue("signal_GUI_needs_update")
        self.process_jobs_queue()
