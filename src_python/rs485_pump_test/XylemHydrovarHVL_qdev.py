#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyQt/Pyside module to provide multithreaded communication and periodical data
acquisition for a Xylem Hydrovar HVL variable speed drive (VSD) controller.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/python-dvg-devices"
__date__ = "03-03-2023"
__version__ = "1.0.0"
# pylint: disable=invalid-name, broad-except, multiple-statements

import os
import sys
import time

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
# pylint: disable=import-error, no-name-in-module, unused-import
if QT_LIB == PYQT5:
    from PyQt5 import QtCore, QtGui, QtWidgets as QtWid    # type: ignore
    from PyQt5.QtCore import pyqtSlot as Slot              # type: ignore
    from PyQt5.QtCore import pyqtSignal as Signal          # type: ignore
elif QT_LIB == PYQT6:
    from PyQt6 import QtCore, QtGui, QtWidgets as QtWid    # type: ignore
    from PyQt6.QtCore import pyqtSlot as Slot              # type: ignore
    from PyQt6.QtCore import pyqtSignal as Signal          # type: ignore
elif QT_LIB == PYSIDE2:
    from PySide2 import QtCore, QtGui, QtWidgets as QtWid  # type: ignore
    from PySide2.QtCore import Slot                        # type: ignore
    from PySide2.QtCore import Signal                      # type: ignore
elif QT_LIB == PYSIDE6:
    from PySide6 import QtCore, QtGui, QtWidgets as QtWid  # type: ignore
    from PySide6.QtCore import Slot                        # type: ignore
    from PySide6.QtCore import Signal                      # type: ignore
# pylint: enable=import-error, no-name-in-module, unused-import
# fmt: on

# \end[Mechanism to support both PyQt and PySide]
# -----------------------------------------------

from dvg_debug_functions import dprint, print_fancy_traceback as pft
from dvg_pyqt_controls import create_Toggle_button, SS_TEXTBOX_ERRORS
from dvg_qdeviceio import QDeviceIO, DAQ_TRIGGER
from XylemHydrovarHVL_protocol_RTU import XylemHydrovarHVL, HVL_Mode


class XylemHydrovarHVL_qdev(QDeviceIO):
    """Manages multithreaded communication and periodical data acquisition for
    a Xylem Hydrovar HVL variable speed drive (VSD) controller.

    In addition, it also provides PyQt/PySide GUI objects for control of the
    device. These can be incorporated into your application.

    All device I/O operations will be offloaded to 'workers', each running in
    a newly created thread.

    (*): See 'dvg_qdeviceio.QDeviceIO()' for details.

    Args:
        dev:
            Reference to a 'XylemHydrovarHVL_protocol_RTU.XylemHydrovarHVL'
            instance.

        debug:
            Show debug info in terminal? Warning: Slow! Do not leave on
            unintentionally.

    Main GUI objects:
        qgrp_control (PyQt5.QtWidgets.QGroupBox)
        qgrp_inverter (PyQt5.QtWidgets.QGroupBox)
        qgrp_error_status (PyQt5.QtWidgets.QGroupBox)
    """

    signal_GUI_input_field_update = Signal(int)

    def __init__(
        self,
        dev: XylemHydrovarHVL,
        DAQ_trigger=DAQ_TRIGGER.INTERNAL_TIMER,
        DAQ_interval_ms=100,
        DAQ_timer_type=QtCore.Qt.TimerType.PreciseTimer,
        critical_not_alive_count=3,
        debug=False,
        **kwargs,
    ):
        super().__init__(dev, **kwargs)  # Pass kwargs onto QtCore.QObject()
        self.dev: XylemHydrovarHVL

        self.create_worker_DAQ(
            DAQ_trigger=DAQ_trigger,
            DAQ_function=self.DAQ_function,
            DAQ_interval_ms=DAQ_interval_ms,
            DAQ_timer_type=DAQ_timer_type,
            critical_not_alive_count=critical_not_alive_count,
            debug=debug,
        )
        self.create_worker_jobs(jobs_function=self.jobs_function, debug=debug)

        self.create_GUI()
        self.signal_DAQ_updated.connect(self.update_GUI)
        # self.signal_connection_lost.connect(self.update_GUI)
        # self.signal_GUI_input_field_update.connect(self.update_GUI_input_field)

        self.update_GUI()
        # self.update_GUI_input_field()

    # --------------------------------------------------------------------------
    #   DAQ_function
    # --------------------------------------------------------------------------

    def DAQ_function(self):
        """Every DAQ time step, read the actual pressure and inverter frequency,
        device status and error status. Every N'th time step, read the inverter
        diagnostics.
        """
        DEBUG_local = True
        if DEBUG_local:
            tick = time.perf_counter()

        success = self.dev.read_error_status()
        success &= self.dev.read_device_status()
        success &= self.dev.read_actual_pressure()
        success &= self.dev.read_actual_frequency()

        if (self.update_counter_DAQ % 5) == 0:
            success &= self.dev.read_inverter_diagnostics()

        if not success:
            return False

        if DEBUG_local:
            tock = time.perf_counter()
            dprint(f"{self.dev.name}: done in {tock - tick:.3f}")

        return True

    # --------------------------------------------------------------------------
    #   jobs_function
    # --------------------------------------------------------------------------

    def jobs_function(self, func, args):
        if func == "signal_GUI_input_field_update":
            # Special instruction
            self.signal_GUI_input_field_update.emit(*args)
        else:
            # Default job processing:
            # Send I/O operation to the device
            try:
                func(*args)
            except Exception as err:
                pft(err)

    # --------------------------------------------------------------------------
    #   create GUI
    # --------------------------------------------------------------------------

    def create_GUI(self):
        # Textbox widths for fitting N characters using the current font
        ex8 = 8 + 8 * QtGui.QFontMetrics(QtGui.QFont()).averageCharWidth()
        p = {
            "alignment": QtCore.Qt.AlignmentFlag.AlignRight,
            "minimumWidth": ex8,
            "maximumWidth": ex8,
        }

        # Pump control
        self.pbtn_pump_running = create_Toggle_button("Not running")
        self.pbtn_pump_running.clicked.connect(self.process_pbtn_pump_running)
        self.rbtn_mode_pressure = QtWid.QRadioButton("Regulate pressure")
        self.rbtn_mode_frequency = QtWid.QRadioButton("Fixed frequency")
        self.qled_P_wanted = QtWid.QLineEdit("nan", **p)
        self.qled_P_actual = QtWid.QLineEdit("nan", **p, readOnly=True)
        self.qled_P_limits = QtWid.QLineEdit(
            f"0 \u2013 {self.dev.max_pressure_setpoint_bar:.2f}",
            **p,
            readOnly=True,
        )
        self.qled_f_wanted = QtWid.QLineEdit("nan", **p)
        self.qled_f_actual = QtWid.QLineEdit("nan", **p, readOnly=True)
        self.qled_f_limits = QtWid.QLineEdit(
            f"{self.dev.state.min_frequency:.0f} \u2013 "
            f"{self.dev.state.max_frequency:.0f}",
            **p,
            readOnly=True,
        )
        self.qlbl_update_counter = QtWid.QLabel("0")

        # fmt: off
        i = 0
        grid = QtWid.QGridLayout()
        grid.setVerticalSpacing(4)

        grid.addWidget(self.pbtn_pump_running          , i, 0, 1, 3); i+=1
        grid.addItem(QtWid.QSpacerItem(1, 10)          , i, 0)      ; i+=1

        grid.addWidget(QtWid.QLabel("<b>Mode</b>")     , i, 0, 1, 3); i+=1
        grid.addItem(QtWid.QSpacerItem(1, 6)           , i, 0)      ; i+=1
        grid.addWidget(self.rbtn_mode_pressure         , i, 0, 1, 3); i+=1
        grid.addWidget(self.rbtn_mode_frequency        , i, 0, 1, 3); i+=1
        grid.addItem(QtWid.QSpacerItem(1, 10)          , i, 0)      ; i+=1

        grid.addWidget(QtWid.QLabel("<b>Pressure</b>") , i, 0, 1, 3); i+=1
        grid.addItem(QtWid.QSpacerItem(1, 6)           , i, 0)      ; i+=1
        grid.addWidget(QtWid.QLabel("Wanted")          , i, 0)
        grid.addWidget(self.qled_P_wanted              , i, 1)
        grid.addWidget(QtWid.QLabel("bar")             , i, 2)      ; i+=1
        grid.addWidget(QtWid.QLabel("Actual")          , i, 0)
        grid.addWidget(self.qled_P_actual              , i, 1)
        grid.addWidget(QtWid.QLabel("bar")             , i, 2)      ; i+=1
        grid.addWidget(QtWid.QLabel("Limits")          , i, 0)
        grid.addWidget(self.qled_P_limits              , i, 1)
        grid.addWidget(QtWid.QLabel("bar")             , i, 2)      ; i+=1
        grid.addItem(QtWid.QSpacerItem(1, 10)          , i, 0)      ; i+=1

        grid.addWidget(QtWid.QLabel("<b>Frequency</b>"), i, 0, 1, 3); i+=1
        grid.addItem(QtWid.QSpacerItem(1, 6)           , i, 0)      ; i+=1
        grid.addWidget(QtWid.QLabel("Wanted")          , i, 0)
        grid.addWidget(self.qled_f_wanted              , i, 1)
        grid.addWidget(QtWid.QLabel("Hz")              , i, 2)      ; i+=1
        grid.addWidget(QtWid.QLabel("Actual")          , i, 0)
        grid.addWidget(self.qled_f_actual              , i, 1)
        grid.addWidget(QtWid.QLabel("Hz")              , i, 2)      ; i+=1
        grid.addWidget(QtWid.QLabel("Limits")          , i, 0)
        grid.addWidget(self.qled_f_limits              , i, 1)
        grid.addWidget(QtWid.QLabel("Hz")              , i, 2)      ; i+=1
        grid.addItem(QtWid.QSpacerItem(1, 10)          , i, 0)      ; i+=1
        grid.addWidget(self.qlbl_update_counter        , i, 0)
        # fmt: on

        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 0)
        grid.setColumnStretch(2, 1)
        grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self.qgrp_control = QtWid.QGroupBox("Pump control")
        self.qgrp_control.setLayout(grid)

        # Inverter diagnostics
        self.qled_inverter_temp = QtWid.QLineEdit("nan", **p, readOnly=True)
        self.qled_inverter_curr_A = QtWid.QLineEdit("nan", **p, readOnly=True)
        self.qled_inverter_curr_pct = QtWid.QLineEdit("nan", **p, readOnly=True)
        self.qled_inverter_volt = QtWid.QLineEdit("nan", **p, readOnly=True)

        # fmt: off
        i = 0
        grid = QtWid.QGridLayout()
        grid.setVerticalSpacing(4)

        grid.addWidget(QtWid.QLabel("Temperature")     , i, 0)
        grid.addWidget(self.qled_inverter_temp         , i, 1)
        grid.addWidget(QtWid.QLabel("\u00b0C")         , i, 2)      ; i+=1
        grid.addWidget(QtWid.QLabel("Voltage")         , i, 0)
        grid.addWidget(self.qled_inverter_volt         , i, 1)
        grid.addWidget(QtWid.QLabel("V")               , i, 2)      ; i+=1
        grid.addWidget(QtWid.QLabel("Current")         , i, 0)
        grid.addWidget(self.qled_inverter_curr_A       , i, 1)
        grid.addWidget(QtWid.QLabel("A")               , i, 2)      ; i+=1
        grid.addWidget(QtWid.QLabel("Current")         , i, 0)
        grid.addWidget(self.qled_inverter_curr_pct     , i, 1)
        grid.addWidget(QtWid.QLabel("%")               , i, 2)      ; i+=1
        # fmt: on

        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 0)
        grid.setColumnStretch(2, 1)
        grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self.qgrp_inverter = QtWid.QGroupBox("Inverter")
        self.qgrp_inverter.setLayout(grid)

        # Error status
        self.error_status = QtWid.QPlainTextEdit()
        self.error_status.setStyleSheet(SS_TEXTBOX_ERRORS)
        self.error_status.setReadOnly(True)

        grid = QtWid.QGridLayout()
        grid.setVerticalSpacing(4)
        grid.addWidget(self.error_status, 0, 0)
        grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self.qgrp_error_status = QtWid.QGroupBox("Error status")
        self.qgrp_error_status.setLayout(grid)

    # --------------------------------------------------------------------------
    #   update_GUI
    # --------------------------------------------------------------------------

    @Slot()
    def update_GUI(self):
        """NOTE: 'self.dev.mutex' is not being locked, because we are only
        reading 'state' for displaying purposes. We can do this because 'state'
        members are written and read atomicly.
        Not locking the mutex might speed up the program.
        """
        state = self.dev.state  # Shorthand

        if self.dev.is_alive:
            if self.update_counter_DAQ == 1:
                # At startup
                if state.hvl_mode == HVL_Mode.CONTROLLER:
                    self.rbtn_mode_pressure.setChecked(True)
                if state.hvl_mode == HVL_Mode.ACTUATOR:
                    self.rbtn_mode_frequency.setChecked(True)

            self.qled_P_actual.setText(f"{state.actual_pressure:.2f}")
            self.qled_f_actual.setText(f"{state.actual_frequency:.1f}")

            self.qled_inverter_temp.setText(f"{state.inverter_temp:.0f}")
            self.qled_inverter_volt.setText(f"{state.inverter_volt:.0f}")
            self.qled_inverter_curr_A.setText(f"{state.inverter_curr_A:.2f}")
            self.qled_inverter_curr_pct.setText(
                f"{state.inverter_curr_pct:.0f}"
            )

            self.qlbl_update_counter.setText(f"{self.update_counter_DAQ}")
        else:
            self.qgrp_control.setEnabled(False)
            self.qgrp_inverter.setEnabled(False)
            self.qgrp_error_status.setEnabled(False)
            self.pbtn_pump_running.setText("OFFLINE")

    # --------------------------------------------------------------------------
    #   GUI functions
    # --------------------------------------------------------------------------

    def process_pbtn_pump_running(self):
        pass
