#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jetting grid
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "17-03-2023"
__version__ = "1.0"
# pylint: disable=bare-except, broad-except, missing-function-docstring, wrong-import-position

import os
import sys
import time

# Constants
DAQ_INTERVAL_MS = 100  # 100 [ms]
DEBUG = False  # Show debug info in terminal?

# Mechanism to support both PyQt and PySide
# -----------------------------------------

PYQT5 = "PyQt5"
PYQT6 = "PyQt6"
PYSIDE2 = "PySide2"
PYSIDE6 = "PySide6"
QT_LIB_ORDER = [PYQT5, PYSIDE2, PYSIDE6, PYQT6]
QT_LIB = None

# Parse optional cli argument to enfore a QT_LIB
# cli example: python benchmark.py pyside6
if len(sys.argv) > 1:
    arg1 = str(sys.argv[1]).upper()
    for i, lib in enumerate(QT_LIB_ORDER):
        if arg1 == lib.upper():
            QT_LIB = lib
            break

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
    from PyQt5 import QtCore, QtWidgets as QtWid           # type: ignore
    from PyQt5.QtCore import pyqtSlot as Slot              # type: ignore
    #from PyQt5.QtCore import pyqtSignal as Signal          # type: ignore
elif QT_LIB == PYQT6:
    from PyQt6 import QtCore, QtWidgets as QtWid           # type: ignore
    from PyQt6.QtCore import pyqtSlot as Slot              # type: ignore
    #from PyQt6.QtCore import pyqtSignal as Signal          # type: ignore
elif QT_LIB == PYSIDE2:
    from PySide2 import QtCore, QtWidgets as QtWid         # type: ignore
    from PySide2.QtCore import Slot                        # type: ignore
    #from PySide2.QtCore import Signal                      # type: ignore
elif QT_LIB == PYSIDE6:
    from PySide6 import QtCore, QtWidgets as QtWid         # type: ignore
    from PySide6.QtCore import Slot                        # type: ignore
    #from PySide6.QtCore import Signal                      # type: ignore
# pylint: enable=import-error, no-name-in-module
# fmt: on

# \end[Mechanism to support both PyQt and PySide]
# -----------------------------------------------

from dvg_debug_functions import dprint, print_fancy_traceback as pft
from dvg_pyqt_filelogger import FileLogger

from dvg_devices.Arduino_protocol_serial import Arduino
from JettingGrid_qdev import JettingGrid_qdev
from JettingGrid_gui import MainWindow

# ------------------------------------------------------------------------------
#   current_date_time_strings
# ------------------------------------------------------------------------------


def current_date_time_strings():
    cur_date_time = QtCore.QDateTime.currentDateTime()
    return (
        cur_date_time.toString("dd-MM-yyyy"),  # Date
        cur_date_time.toString("HH:mm:ss"),  # Time
    )


# ------------------------------------------------------------------------------
#   Program termination routines
# ------------------------------------------------------------------------------


def stop_running():
    app.processEvents()
    ard_qdev.quit()
    logger.close()


@Slot()
def notify_connection_lost():
    stop_running()

    window.qlbl_title.setText("! ! !    LOST CONNECTION    ! ! !")
    str_cur_date, str_cur_time = current_date_time_strings()
    str_msg = f"{str_cur_date} {str_cur_time}\nLost connection to Arduino."
    print("\nCRITICAL ERROR @ {str_msg}")
    reply = QtWid.QMessageBox.warning(
        window, "CRITICAL ERROR", str_msg, QtWid.QMessageBox.Ok
    )

    if reply == QtWid.QMessageBox.Ok:
        pass  # Leave the GUI open for read-only inspection by the user


@Slot()
def about_to_quit():
    print("\nAbout to quit")
    stop_running()
    ard.close()


# ------------------------------------------------------------------------------
#   Arduino data-acquisition update function
# ------------------------------------------------------------------------------


def DAQ_function() -> bool:
    # WARNING: Do not change the GUI directly from out of this function as it
    # will be running in a separate and different thread to the main/GUI thread.

    # Shorthands
    state = ard_qdev.state

    # Date-time keeping
    str_cur_date, str_cur_time = current_date_time_strings()

    # Query the Arduino for its state
    success, reply = ard.query_ascii_values("?", delimiter="\t")
    if not success:
        dprint(f"'{ard.name}' reports IOError @ {str_cur_date} {str_cur_time}")
        return False

    # Parse readings into separate state variables
    try:
        # pylint: disable=unbalanced-tuple-unpacking
        (
            state.P_1_mA,
            state.P_2_mA,
            state.P_3_mA,
            state.P_4_mA,
            state.P_1_bar,
            state.P_2_bar,
            state.P_3_bar,
            state.P_4_bar,
        ) = reply
        # pylint: enable=unbalanced-tuple-unpacking
    except Exception as err:
        pft(err)
        dprint(f"'{ard.name}' reports IOError @ {str_cur_date} {str_cur_time}")
        return False

    # We use PC time
    state.time = time.perf_counter()

    # Add readings to chart histories
    window.curve_pres_1.appendData(state.time, state.P_1_bar)
    window.curve_pres_2.appendData(state.time, state.P_2_bar)
    window.curve_pres_3.appendData(state.time, state.P_3_bar)
    window.curve_pres_4.appendData(state.time, state.P_4_bar)

    # Logging to file
    window.logger.update()

    # Return success
    return True


# ------------------------------------------------------------------------------
#   File logger
# ------------------------------------------------------------------------------


def write_header_to_log():
    str_cur_date, str_cur_time = current_date_time_strings()
    logger.write("[HEADER]\n")
    logger.write(str_cur_date + "\n")
    logger.write(str_cur_time + "\n")
    logger.write(window.qtxt_comments.toPlainText())
    logger.write("\n\n[DATA]\n")
    logger.write("[s]\t[bar]\t[bar]\t[bar]\t[bar]\n")
    logger.write("time\tP_1\tP_2\tP_3\tP_4\n")


def write_data_to_log():
    state = ard_qdev.state  # Shorthand
    logger.write(
        f"{logger.elapsed():.2f}\t"
        f"{state.P_1_bar:.3f}\t{state.P_2_bar:.3f}\t"
        f"{state.P_3_bar:.3f}\t{state.P_4_bar:.3f}\n"
    )


# ------------------------------------------------------------------------------
#   Main
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # Connect to Arduino
    ard = Arduino(name="Ard", connect_to_specific_ID="TWT jetting grid")
    ard.serial_settings["baudrate"] = 115200
    ard.auto_connect(filepath_last_known_port="config/port_Arduino.txt")

    if not ard.is_alive:
        print("\nCheck connection and try resetting the Arduino.\n")
        # print("Exiting...\n")
        # sys.exit(0)

    # Set up multi-threaded communication: Creates workers and threads
    ard_qdev = JettingGrid_qdev(
        dev=ard,
        DAQ_function=DAQ_function,
        DAQ_interval_ms=DAQ_INTERVAL_MS,
        debug=DEBUG,
    )
    ard_qdev.signal_connection_lost.connect(notify_connection_lost)

    # File logger
    logger = FileLogger(
        write_header_function=write_header_to_log,
        write_data_function=write_data_to_log,
    )

    # Create application and main window
    QtCore.QThread.currentThread().setObjectName("MAIN")  # For DEBUG info
    app = QtWid.QApplication(sys.argv)
    app.aboutToQuit.connect(about_to_quit)
    window = MainWindow(ard, ard_qdev, logger, DEBUG)

    # Start threads
    ard_qdev.start()

    # Start the main GUI event loop
    window.show()
    if QT_LIB in (PYQT5, PYSIDE2):
        sys.exit(app.exec_())
    else:
        sys.exit(app.exec())
