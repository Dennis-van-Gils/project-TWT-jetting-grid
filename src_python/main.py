#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jetting grid
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "21-10-2022"
__version__ = "1.0"
# pylint: disable=bare-except, broad-except

import sys
import time

from PyQt5 import QtCore
from PyQt5 import QtWidgets as QtWid
from PyQt5.QtCore import QDateTime

from dvg_pyqt_filelogger import FileLogger
from dvg_debug_functions import dprint, print_fancy_traceback as pft

from dvg_devices.Arduino_protocol_serial import Arduino
from jetting_grid_qdev import JettingGrid_qdev
from jetting_grid_gui import MainWindow

# Globals
DAQ_INTERVAL_MS = 100  # 100 [ms]

# Show debug info in terminal?
DEBUG = False

# ------------------------------------------------------------------------------
#   current_date_time_strings
# ------------------------------------------------------------------------------


def current_date_time_strings():
    cur_date_time = QDateTime.currentDateTime()
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


@QtCore.pyqtSlot()
def notify_connection_lost():
    stop_running()

    window.qlbl_title.setText("! ! !    LOST CONNECTION    ! ! !")
    str_cur_date, str_cur_time = current_date_time_strings()
    str_msg = "%s %s\nLost connection to Arduino." % (
        str_cur_date,
        str_cur_time,
    )
    print("\nCRITICAL ERROR @ %s" % str_msg)
    reply = QtWid.QMessageBox.warning(
        window, "CRITICAL ERROR", str_msg, QtWid.QMessageBox.Ok
    )

    if reply == QtWid.QMessageBox.Ok:
        pass  # Leave the GUI open for read-only inspection by the user


@QtCore.pyqtSlot()
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
    if not (success):
        dprint(f"'{ard.name}' reports IOError @ {str_cur_date} {str_cur_time}")
        return False

    # Parse readings into separate state variables
    try:
        (
            state.pres_1_mA,
            state.pres_2_mA,
            state.pres_3_mA,
            state.pres_4_mA,
            state.pres_1_bar,
            state.pres_2_bar,
            state.pres_3_bar,
            state.pres_4_bar,
        ) = reply
    except Exception as err:
        pft(err)
        dprint(f"'{ard.name}' reports IOError @ {str_cur_date} {str_cur_time}")
        return False

    # We use PC time
    state.time = time.perf_counter()

    # Add readings to chart histories
    window.curve_pres_1.appendData(state.time, state.pres_1_bar)
    window.curve_pres_2.appendData(state.time, state.pres_2_bar)
    window.curve_pres_3.appendData(state.time, state.pres_3_bar)
    window.curve_pres_4.appendData(state.time, state.pres_4_bar)

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
    logger.write("time\tpres_1\tpres_2\tpres_3\tpres_4\n")


def write_data_to_log():
    state = ard_qdev.state  # Shorthand
    logger.write(
        f"{logger.elapsed():.2f}\t"
        f"{state.pres_1_bar:.3f}\t{state.pres_2_bar:.3f}\t"
        f"{state.pres_3_bar:.3f}\t{state.pres_4_bar:.3f}\n"
    )


# ------------------------------------------------------------------------------
#   Main
# ------------------------------------------------------------------------------

if __name__ == "__main__":

    # Connect to Arduino
    ard = Arduino(name="Ard", connect_to_specific_ID="TWT jetting grid")
    ard.serial_settings["baudrate"] = 115200
    ard.auto_connect(filepath_last_known_port="config/port_Arduino.txt")

    if not (ard.is_alive):
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
    window = MainWindow(ard, ard_qdev, logger)

    # Start threads
    ard_qdev.start()

    # Start the main GUI event loop
    window.show()
    sys.exit(app.exec_())
