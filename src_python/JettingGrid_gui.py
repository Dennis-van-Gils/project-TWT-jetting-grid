#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jetting_grid_gui.py

Manages the graphical user interface
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "24-10-2022"
__version__ = "1.0"
# pylint: disable=bare-except, broad-except, unnecessary-lambda

import os
import sys

# Constants
UPDATE_INTERVAL_WALL_CLOCK = 50  # 50 [ms]
CHART_HISTORY_TIME = 7200  # Maximum history length of charts [s]
TRY_USING_OPENGL = True

# Mechanism to support both PyQt and PySide
# -----------------------------------------

PYQT5 = "PyQt5"
PYQT6 = "PyQt6"
PYSIDE2 = "PySide2"
PYSIDE6 = "PySide6"
QT_LIB_ORDER = [PYQT5, PYSIDE2, PYSIDE6, PYQT6]
QT_LIB = os.getenv("PYQTGRAPH_QT_LIB")

# pylint: disable=import-error, no-name-in-module, c-extension-no-member
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
    raise Exception(
        f"{this_file} requires PyQt5, PyQt6, PySide2 or PySide6; "
        "none of these packages could be imported."
    )

# fmt: off
if QT_LIB == PYQT5:
    from PyQt5 import QtCore, QtGui, QtWidgets as QtWid    # type: ignore
    from PyQt5.QtCore import pyqtSlot as Slot              # type: ignore
    #from PyQt5.QtCore import pyqtSignal as Signal          # type: ignore
elif QT_LIB == PYQT6:
    from PyQt6 import QtCore, QtGui, QtWidgets as QtWid    # type: ignore
    from PyQt6.QtCore import pyqtSlot as Slot              # type: ignore
    #from PyQt6.QtCore import pyqtSignal as Signal          # type: ignore
elif QT_LIB == PYSIDE2:
    from PySide2 import QtCore, QtGui, QtWidgets as QtWid  # type: ignore
    from PySide2.QtCore import Slot                        # type: ignore
    #from PySide2.QtCore import Signal                      # type: ignore
elif QT_LIB == PYSIDE6:
    from PySide6 import QtCore, QtGui, QtWidgets as QtWid  # type: ignore
    from PySide6.QtCore import Slot                        # type: ignore
    #from PySide6.QtCore import Signal                      # type: ignore
# fmt: on

QT_VERSION = (
    QtCore.QT_VERSION_STR if QT_LIB in (PYQT5, PYQT6) else QtCore.__version__
)

# pylint: enable=import-error, no-name-in-module, c-extension-no-member
# \end[Mechanism to support both PyQt and PySide]
# -----------------------------------------------

import pyqtgraph as pg

print(f"{QT_LIB:9s} {QT_VERSION}")
print(f"PyQtGraph {pg.__version__}")

if TRY_USING_OPENGL:
    try:
        import OpenGL.GL as gl  # pylint: disable=unused-import
        from OpenGL.version import __version__ as gl_version
    except:
        print("PyOpenGL  not found")
        print("To install: `conda install pyopengl` or `pip install pyopengl`")
    else:
        print(f"PyOpenGL  {gl_version}")
        pg.setConfigOptions(useOpenGL=True)
        pg.setConfigOptions(antialias=True)
        pg.setConfigOptions(enableExperimental=True)
else:
    print("PyOpenGL  disabled")

from dvg_debug_functions import tprint
from dvg_pyqt_filelogger import FileLogger
import dvg_pyqt_controls as controls
from dvg_pyqtgraph_threadsafe import (
    HistoryChartCurve,
    LegendSelect,
    PlotManager,
)

from dvg_devices.Arduino_protocol_serial import Arduino
from JettingGrid_qdev import JettingGrid_qdev


# Default settings for graphs
# pg.setConfigOptions(leftButtonPan=False)
pg.setConfigOption("background", controls.COLOR_GRAPH_BG)
pg.setConfigOption("foreground", controls.COLOR_GRAPH_FG)


# ------------------------------------------------------------------------------
#   Custom plotting styles
# ------------------------------------------------------------------------------


class CustomAxis(pg.AxisItem):
    """Aligns the top label of a `pyqtgraph.PlotItem` plot to the top-left
    corner
    """

    def resizeEvent(self, ev=None):
        if self.orientation == "top":
            self.label.setPos(QtCore.QPointF(0, 0))


def apply_PlotItem_style(
    pi: pg.PlotItem,
    title: str = "",
    bottom: str = "",
    left: str = "",
    right: str = "",
):
    """Apply our custom stylesheet to a `pyqtgraph.PlotItem` plot"""

    pi.setClipToView(True)
    pi.showGrid(x=1, y=1)
    pi.setMenuEnabled(True)
    pi.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
    pi.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
    pi.setAutoVisible(y=True)
    pi.setRange(xRange=[-CHART_HISTORY_TIME, 0])
    pi.vb.setLimits(xMax=0.01)

    p_title = {
        "color": controls.COLOR_GRAPH_FG.name(),
        "font-size": "12pt",
        "font-family": "Helvetica",
        "font-weight": "bold",
    }
    p_label = {
        "color": controls.COLOR_GRAPH_FG.name(),
        "font-size": "12pt",
        "font-family": "Helvetica",
    }
    pi.setLabel("bottom", bottom, **p_label)
    pi.setLabel("left", left, **p_label)
    pi.setLabel("top", title, **p_title)
    pi.setLabel("right", right, **p_label)

    # fmt: off
    font = QtGui.QFont()
    font.setPixelSize(16)
    pi.getAxis("bottom").setTickFont(font)
    pi.getAxis("left")  .setTickFont(font)
    pi.getAxis("top")   .setTickFont(font)
    pi.getAxis("right") .setTickFont(font)

    pi.getAxis("bottom").setStyle(tickTextOffset=10)
    pi.getAxis("left")  .setStyle(tickTextOffset=10)

    pi.getAxis("bottom").setHeight(60)
    pi.getAxis("left")  .setWidth(90)
    pi.getAxis("top")   .setHeight(40)
    pi.getAxis("right") .setWidth(16)

    pi.getAxis("top")  .setStyle(showValues=False)
    pi.getAxis("right").setStyle(showValues=False)
    # fmt: on


# ------------------------------------------------------------------------------
#   MainWindow
# ------------------------------------------------------------------------------


class MainWindow(QtWid.QWidget):
    def __init__(
        self,
        ard: Arduino,
        ard_qdev: JettingGrid_qdev,
        logger: FileLogger,
        debug: bool = False,
        parent=None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self.ard = ard
        self.ard_qdev = ard_qdev
        self.logger = logger
        self.debug = debug

        # Shorthands
        state = self.ard_qdev.state

        self.setWindowTitle("Jetting grid")
        self.setGeometry(350, 60, 1200, 900)
        self.setStyleSheet(
            controls.SS_TEXTBOX_READ_ONLY
            + controls.SS_GROUP
            + controls.SS_HOVER
        )

        # Textbox widths for fitting N characters using the current font
        ex8 = 8 + 8 * QtGui.QFontMetrics(QtGui.QFont()).averageCharWidth()
        ex10 = 8 + 10 * QtGui.QFontMetrics(QtGui.QFont()).averageCharWidth()

        # -------------------------
        #   Top frame
        # -------------------------

        # Left box
        self.qlbl_update_counter = QtWid.QLabel("0")
        self.qlbl_DAQ_rate = QtWid.QLabel("DAQ: nan Hz")
        self.qlbl_DAQ_rate.setStyleSheet("QLabel {min-width: 7em}")
        self.qlbl_recording_time = QtWid.QLabel()

        vbox_left = QtWid.QVBoxLayout()
        vbox_left.addWidget(self.qlbl_update_counter, stretch=0)
        vbox_left.addStretch(1)
        vbox_left.addWidget(self.qlbl_recording_time, stretch=0)
        vbox_left.addWidget(self.qlbl_DAQ_rate, stretch=0)

        # Middle box
        self.qlbl_title = QtWid.QLabel(
            "Jetting grid",
            font=QtGui.QFont("Palatino", 14, weight=QtGui.QFont.Weight.Bold),
        )
        self.qlbl_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.qlbl_cur_date_time = QtWid.QLabel("00-00-0000    00:00:00")
        self.qlbl_cur_date_time.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.qpbt_record = controls.create_Toggle_button(
            "Click to start recording to file"
        )
        self.qpbt_record.clicked.connect(
            lambda state: self.logger.record(state)
        )

        vbox_middle = QtWid.QVBoxLayout()
        vbox_middle.addWidget(self.qlbl_title)
        vbox_middle.addWidget(self.qlbl_cur_date_time)
        vbox_middle.addWidget(self.qpbt_record)

        # Right box
        p = {
            "alignment": QtCore.Qt.AlignmentFlag.AlignRight
            | QtCore.Qt.AlignmentFlag.AlignVCenter
        }
        self.qpbt_exit = QtWid.QPushButton("Exit", minimumHeight=30)
        self.qpbt_exit.clicked.connect(self.close)
        self.qlbl_GitHub = QtWid.QLabel(
            f'<a href="{__url__}">GitHub source</a>', **p
        )
        self.qlbl_GitHub.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.qlbl_GitHub.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.qlbl_GitHub.setOpenExternalLinks(True)

        vbox_right = QtWid.QVBoxLayout(spacing=4)
        vbox_right.addWidget(self.qpbt_exit, stretch=0)
        vbox_right.addStretch(1)
        vbox_right.addWidget(QtWid.QLabel(__author__, **p))
        vbox_right.addWidget(self.qlbl_GitHub)
        vbox_right.addWidget(QtWid.QLabel(f"v{__version__}", **p))

        # Round up top frame
        hbox_top = QtWid.QHBoxLayout()
        hbox_top.addLayout(vbox_left, stretch=0)
        hbox_top.addStretch(1)
        hbox_top.addLayout(vbox_middle, stretch=0)
        hbox_top.addStretch(1)
        hbox_top.addLayout(vbox_right, stretch=0)

        # -------------------------
        #   Bottom frame
        # -------------------------

        #  Charts
        # -------------------------

        self.gw = pg.GraphicsLayoutWidget()

        # Plots
        self.pi_pres = self.gw.addPlot(
            row=0, col=0, axisItems={"top": CustomAxis(orientation="top")}
        )
        apply_PlotItem_style(self.pi_pres, title="Pressure", left="bar")
        self.plots = [self.pi_pres]

        # Thread-safe curves
        capacity = round(
            CHART_HISTORY_TIME * 1e3 / ard_qdev.worker_DAQ._DAQ_interval_ms
        )
        PEN_01 = pg.mkPen(controls.COLOR_PEN_TURQUOISE, width=3)
        PEN_02 = pg.mkPen(controls.COLOR_PEN_YELLOW, width=3)
        PEN_03 = pg.mkPen(controls.COLOR_PEN_PINK, width=3)
        PEN_04 = pg.mkPen(controls.COLOR_PEN_BLUE, width=3)

        self.curve_pres_1 = HistoryChartCurve(
            capacity=capacity,
            linked_curve=self.pi_pres.plot(pen=PEN_01, name="P_1"),
        )
        self.curve_pres_2 = HistoryChartCurve(
            capacity=capacity,
            linked_curve=self.pi_pres.plot(pen=PEN_02, name="P_2"),
        )
        self.curve_pres_3 = HistoryChartCurve(
            capacity=capacity,
            linked_curve=self.pi_pres.plot(pen=PEN_03, name="P_3"),
        )
        self.curve_pres_4 = HistoryChartCurve(
            capacity=capacity,
            linked_curve=self.pi_pres.plot(pen=PEN_04, name="P_4"),
        )

        # TODO: Add pump velocity and setpoint plots & curves

        self.curves_pres = [
            self.curve_pres_1,
            self.curve_pres_2,
            self.curve_pres_3,
            self.curve_pres_4,
        ]
        self.curves = self.curves_pres

        #  Group `Readings`
        # -------------------------

        legend_1 = LegendSelect(linked_curves=self.curves_pres)
        legend_1.qpbt_toggle.clicked.connect(
            lambda: QtCore.QCoreApplication.processEvents()  # Force redraw
        )

        p = {
            "readOnly": True,
            "alignment": QtCore.Qt.AlignmentFlag.AlignRight,
            "maximumWidth": ex8,
        }
        self.qlin_pres_1 = QtWid.QLineEdit(**p)
        self.qlin_pres_2 = QtWid.QLineEdit(**p)
        self.qlin_pres_3 = QtWid.QLineEdit(**p)
        self.qlin_pres_4 = QtWid.QLineEdit(**p)

        # fmt: off
        legend_1.grid.setHorizontalSpacing(6)
        legend_1.grid.addWidget(self.qlin_pres_1   , 0, 2)
        legend_1.grid.addWidget(QtWid.QLabel("bar"), 0, 3)
        legend_1.grid.addWidget(self.qlin_pres_2   , 1, 2)
        legend_1.grid.addWidget(QtWid.QLabel("bar"), 1, 3)
        legend_1.grid.addWidget(self.qlin_pres_3   , 2, 2)
        legend_1.grid.addWidget(QtWid.QLabel("bar"), 2, 3)
        legend_1.grid.addWidget(self.qlin_pres_4   , 3, 2)
        legend_1.grid.addWidget(QtWid.QLabel("bar"), 3, 3)
        legend_1.grid.setColumnStretch(0, 0)
        legend_1.grid.setColumnStretch(1, 0)
        # fmt: on

        vbox = QtWid.QVBoxLayout(spacing=4)
        vbox.addWidget(QtWid.QLabel("<b>Pressure</b>"))
        vbox.addLayout(legend_1.grid)
        # vbox.addSpacing(6)

        qgrp_readings = QtWid.QGroupBox("Readings")
        qgrp_readings.setLayout(vbox)

        #  Group 'Log comments'
        # -------------------------

        self.qtxt_comments = QtWid.QTextEdit()
        self.qtxt_comments.setMinimumHeight(60)
        grid = QtWid.QGridLayout()
        grid.addWidget(self.qtxt_comments, 0, 0)

        qgrp_comments = QtWid.QGroupBox("Log comments")
        qgrp_comments.setLayout(grid)

        #  Group 'Charts'
        # -------------------------

        self.plot_manager = PlotManager(parent=self)
        self.plot_manager.add_autorange_buttons(linked_plots=self.plots)
        self.plot_manager.add_preset_buttons(
            linked_plots=self.plots,
            linked_curves=self.curves,
            presets=[
                {
                    "button_label": "01:00",
                    "x_axis_label": "sec",
                    "x_axis_divisor": 1,
                    "x_axis_range": (-60, 0),
                },
                {
                    "button_label": "03:00",
                    "x_axis_label": "sec",
                    "x_axis_divisor": 1,
                    "x_axis_range": (-180, 0),
                },
                {
                    "button_label": "10:00",
                    "x_axis_label": "min",
                    "x_axis_divisor": 60,
                    "x_axis_range": (-10, 0),
                },
                {
                    "button_label": "30:00",
                    "x_axis_label": "min",
                    "x_axis_divisor": 60,
                    "x_axis_range": (-30, 0),
                },
                {
                    "button_label": "60:00",
                    "x_axis_label": "min",
                    "x_axis_divisor": 60,
                    "x_axis_range": (-60, 0),
                },
                {
                    "button_label": "120:00",
                    "x_axis_label": "min",
                    "x_axis_divisor": 60,
                    "x_axis_range": (-120, 0),
                },
            ],
        )
        self.plot_manager.add_clear_button(linked_curves=self.curves)
        self.plot_manager.perform_preset(1)

        qgrp_charts = QtWid.QGroupBox("Charts")
        qgrp_charts.setLayout(self.plot_manager.grid)

        #  Round up bottom frame
        # -------------------------

        vbox = QtWid.QVBoxLayout()
        vbox.addWidget(qgrp_readings)
        vbox.addWidget(qgrp_comments)
        vbox.addWidget(qgrp_charts)

        grid_bot = QtWid.QGridLayout()
        grid_bot.addWidget(self.gw, 0, 0)
        grid_bot.addLayout(vbox, 0, 1)
        grid_bot.setColumnStretch(0, 1)
        grid_bot.setColumnStretch(1, 0)

        # -------------------------
        #   Round up full window
        # -------------------------

        vbox = QtWid.QVBoxLayout(self)
        vbox.addLayout(hbox_top, stretch=0)
        vbox.addSpacerItem(QtWid.QSpacerItem(0, 10))
        vbox.addLayout(grid_bot, stretch=1)

        # -------------------------
        #   Wall clock timer
        # -------------------------

        self.timer_wall_clock = QtCore.QTimer()
        self.timer_wall_clock.timeout.connect(self.update_wall_clock)
        self.timer_wall_clock.start(UPDATE_INTERVAL_WALL_CLOCK)

        # -------------------------
        #   Connect external signals
        # -------------------------

        self.ard_qdev.signal_DAQ_updated.connect(self.update_GUI)

        self.logger.signal_recording_started.connect(
            lambda filepath: self.qpbt_record.setText(
                f"Recording to file: {filepath}"
            )
        )
        self.logger.signal_recording_stopped.connect(
            lambda: self.qpbt_record.setText("Click to start recording to file")
        )

    # --------------------------------------------------------------------------
    #   Handle controls
    # --------------------------------------------------------------------------

    @Slot()
    def update_wall_clock(self):
        cur_date_time = QtCore.QDateTime.currentDateTime()
        self.qlbl_cur_date_time.setText(
            f"{cur_date_time.toString('dd-MM-yyyy')}    "
            f"{cur_date_time.toString('HH:mm:ss')}"
        )

    @Slot()
    def update_GUI(self):
        # Shorthands
        ard_qdev = self.ard_qdev
        state = self.ard_qdev.state

        self.qlbl_update_counter.setText(f"{ard_qdev.update_counter_DAQ}")
        self.qlbl_DAQ_rate.setText(
            f"DAQ: {ard_qdev.obtained_DAQ_rate_Hz:.1f} Hz"
        )
        self.qlbl_recording_time.setText(
            f"REC: {self.logger.pretty_elapsed()}"
            if self.logger.is_recording()
            else ""
        )

        self.qlin_pres_1.setText(f"{state.pres_1_bar:.3f}")
        self.qlin_pres_2.setText(f"{state.pres_2_bar:.3f}")
        self.qlin_pres_3.setText(f"{state.pres_3_bar:.3f}")
        self.qlin_pres_4.setText(f"{state.pres_4_bar:.3f}")

        if self.debug:
            tprint("update_charts")

        for curve in self.curves:
            curve.update()