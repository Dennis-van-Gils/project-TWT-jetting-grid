#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JettingGrid_gui.py

Manages the graphical user interface, tying together the Jetting Grid Arduino
and the Xylem Hydrovar HVL pump.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "17-04-2023"
__version__ = "1.0"
# pylint: disable=bare-except, broad-except, unnecessary-lambda, wrong-import-position

import os
import sys
from functools import partial
from pathlib import Path

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
    from PyQt5 import QtCore, QtGui, QtWidgets as QtWid    # type: ignore
    from PyQt5.QtCore import pyqtSlot as Slot              # type: ignore
elif QT_LIB == PYQT6:
    from PyQt6 import QtCore, QtGui, QtWidgets as QtWid    # type: ignore
    from PyQt6.QtCore import pyqtSlot as Slot              # type: ignore
elif QT_LIB == PYSIDE2:
    from PySide2 import QtCore, QtGui, QtWidgets as QtWid  # type: ignore
    from PySide2.QtCore import Slot                        # type: ignore
elif QT_LIB == PYSIDE6:
    from PySide6 import QtCore, QtGui, QtWidgets as QtWid  # type: ignore
    from PySide6.QtCore import Slot                        # type: ignore
# pylint: enable=import-error, no-name-in-module
# fmt: on

# pylint: disable=c-extension-no-member
QT_VERSION = (
    QtCore.QT_VERSION_STR if QT_LIB in (PYQT5, PYQT6) else QtCore.__version__
)
# pylint: enable=c-extension-no-member

# \end[Mechanism to support both PyQt and PySide]
# -----------------------------------------------

import pyqtgraph as pg
import qtawesome as qta

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

from JettingGrid_Arduino import JettingGrid_Arduino
from JettingGrid_qdev import JettingGrid_qdev, GUI_objects
from JettingGrid_upload import upload_protocol
from XylemHydrovarHVL_protocol_RTU import XylemHydrovarHVL
from XylemHydrovarHVL_qdev import XylemHydrovarHVL_qdev

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
        grid_qdev: JettingGrid_qdev,
        pump_qdev: XylemHydrovarHVL_qdev,
        logger: FileLogger,
        debug: bool = False,
        parent=None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self.grid_qdev = grid_qdev
        self.pump_qdev = pump_qdev
        self.logger = logger
        self.debug = debug

        # Shorthands to the low-level devices
        self.grid: JettingGrid_Arduino = self.grid_qdev.dev
        self.pump: XylemHydrovarHVL = self.pump_qdev.dev

        self.create_GUI()

    def create_GUI(self):
        self.setWindowTitle("Jetting Grid")
        self.setGeometry(150, 60, 1200, 800)
        self.setStyleSheet(
            controls.SS_TEXTBOX_READ_ONLY
            + controls.SS_GROUP
            + controls.SS_HOVER
        )

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
        icon = "fa.fighter-jet"
        self.icon_1 = QtWid.QLabel()
        self.icon_1.setPixmap(qta.icon(icon).pixmap(28, 28))
        self.icon_1.setVisible(False)
        self.icon_2 = QtWid.QLabel()
        self.icon_2.setPixmap(qta.icon(icon, hflip=False).pixmap(28, 28))
        self.icon_2.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.icon_2.setVisible(False)

        self.qlbl_title = QtWid.QLabel(
            "Jetting Grid",
            font=QtGui.QFont("Palatino", 14, weight=QtGui.QFont.Weight.Bold),
        )
        self.qlbl_title.mousePressEvent = self.toggle_icons
        self.qlbl_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.qlbl_cur_date_time = QtWid.QLabel("00-00-0000    00:00:00")
        self.qlbl_cur_date_time.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.qpbt_record = controls.create_Toggle_button(
            "Click to start recording to file"
        )
        self.qpbt_record.setMinimumWidth(controls.e8(32))
        self.qpbt_record.clicked.connect(
            lambda state: self.logger.record(state)
        )

        hbox_title = QtWid.QHBoxLayout()
        hbox_title.addWidget(self.icon_1)
        hbox_title.addWidget(self.qlbl_title)
        hbox_title.addWidget(self.icon_2)

        vbox_middle = QtWid.QVBoxLayout()
        vbox_middle.addLayout(hbox_title)
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

        #  Pump control
        # -------------------------

        self.pump_qdev.qpte_error_status.setMaximumWidth(controls.e8(20))
        self.pump_qdev.qpte_error_status.setMinimumWidth(controls.e8(20))

        vbox_pump = QtWid.QVBoxLayout()
        vbox_pump.addWidget(self.pump_qdev.qgrp_control)
        vbox_pump.addWidget(self.pump_qdev.qgrp_inverter)
        vbox_pump.addWidget(self.pump_qdev.qgrp_error_status)

        #  Protocol control
        # -------------------------

        gq = self.grid_qdev  # Even shorter shorthand
        qbtn_width = controls.e8(5)

        self.qpbt_proto_play = QtWid.QPushButton("")
        self.qpbt_proto_play.setFixedWidth(qbtn_width)
        self.qpbt_proto_play.setIcon(qta.icon("mdi6.play"))
        self.qpbt_proto_play.clicked.connect(gq.send_play_protocol)

        self.qpbt_proto_pause = QtWid.QPushButton("")
        self.qpbt_proto_pause.setFixedWidth(qbtn_width)
        self.qpbt_proto_pause.setIcon(qta.icon("mdi6.pause"))
        self.qpbt_proto_pause.clicked.connect(gq.send_pause_protocol)

        self.qpbt_proto_stop = QtWid.QPushButton("")
        self.qpbt_proto_stop.setFixedWidth(qbtn_width)
        self.qpbt_proto_stop.setIcon(qta.icon("mdi6.stop"))
        self.qpbt_proto_stop.clicked.connect(self.process_qpbt_proto_stop)

        self.qpbt_proto_rewind = QtWid.QPushButton("")
        self.qpbt_proto_rewind.setFixedWidth(qbtn_width)
        self.qpbt_proto_rewind.setIcon(qta.icon("mdi6.skip-backward"))
        self.qpbt_proto_rewind.clicked.connect(gq.send_rewind_protocol)

        self.qpbt_proto_prevline = QtWid.QPushButton("")
        self.qpbt_proto_prevline.setFixedWidth(qbtn_width)
        self.qpbt_proto_prevline.setIcon(qta.icon("mdi6.step-backward"))
        self.qpbt_proto_prevline.clicked.connect(gq.send_prevline_protocol)

        self.qpbt_proto_nextline = QtWid.QPushButton("")
        self.qpbt_proto_nextline.setFixedWidth(qbtn_width)
        self.qpbt_proto_nextline.setIcon(qta.icon("mdi6.step-forward"))
        self.qpbt_proto_nextline.clicked.connect(gq.send_nextline_protocol)

        self.qpbt_proto_gotoline = QtWid.QPushButton("")
        self.qpbt_proto_gotoline.setFixedWidth(qbtn_width)
        self.qpbt_proto_gotoline.setIcon(qta.icon("mdi6.arrow-down-right-bold"))
        self.qpbt_proto_gotoline.clicked.connect(
            self.process_qpbt_proto_gotoline
        )

        self.qpbt_proto_upload = QtWid.QPushButton("Upload file")
        self.qpbt_proto_upload.clicked.connect(self.process_qpbt_proto_upload)

        self.qpbt_proto_pos = QtWid.QLineEdit("", readOnly=True)
        self.qlin_proto_name = QtWid.QLineEdit(
            self.grid.state.protocol_name, readOnly=True
        )

        # fmt: off
        qgrid_protocol = QtWid.QGridLayout()
        qgrid_protocol.addWidget(self.qpbt_proto_play    , 0, 0)
        qgrid_protocol.addWidget(self.qpbt_proto_pause   , 0, 1)
        qgrid_protocol.addWidget(self.qpbt_proto_stop    , 0, 2)
        qgrid_protocol.addWidget(self.qpbt_proto_rewind  , 1, 0)
        qgrid_protocol.addWidget(self.qpbt_proto_prevline, 1, 1)
        qgrid_protocol.addWidget(self.qpbt_proto_nextline, 1, 2)
        qgrid_protocol.addWidget(self.qpbt_proto_gotoline, 2, 0)
        qgrid_protocol.addWidget(self.qpbt_proto_pos     , 2, 1, 1, 2)

        self.qpbt_preset_0 = QtWid.QPushButton("Preset 0\n└ Open all valves")
        self.qpbt_preset_1 = QtWid.QPushButton("Preset 1\n└ Walk over valves")
        self.qpbt_preset_2 = QtWid.QPushButton("Preset 2\n└ Walk over manifolds")
        self.qpbt_preset_3 = QtWid.QPushButton("Preset 3\n└ Checkerboard")
        self.qpbt_preset_4 = QtWid.QPushButton("Preset 4\n└ Even/odd valves")
        # fmt: on

        qpbts_presets = [
            self.qpbt_preset_0,
            self.qpbt_preset_1,
            self.qpbt_preset_2,
            self.qpbt_preset_3,
            self.qpbt_preset_4,
        ]
        for idx, qpbt in enumerate(qpbts_presets):
            qpbt.setStyleSheet("text-align:left;")
            qpbt.clicked.connect(partial(self.process_qpbtn_preset, idx))

        vbox_protocol = QtWid.QVBoxLayout(spacing=4)
        vbox_protocol.addWidget(self.qpbt_proto_upload)
        vbox_protocol.addSpacerItem(QtWid.QSpacerItem(0, 20))
        vbox_protocol.addWidget(self.qlin_proto_name)
        vbox_protocol.addLayout(qgrid_protocol)
        vbox_protocol.addSpacerItem(QtWid.QSpacerItem(0, 20))
        vbox_protocol.addWidget(self.qpbt_preset_0)
        vbox_protocol.addWidget(self.qpbt_preset_1)
        vbox_protocol.addWidget(self.qpbt_preset_2)
        vbox_protocol.addWidget(self.qpbt_preset_3)
        vbox_protocol.addWidget(self.qpbt_preset_4)

        qgrp_protocol = QtWid.QGroupBox("Protocol")
        qgrp_protocol.setLayout(vbox_protocol)

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
            CHART_HISTORY_TIME
            * 1e3
            / self.grid_qdev.worker_DAQ._DAQ_interval_ms
        )
        PEN_01 = pg.mkPen(controls.COLOR_PEN_RED, width=3)
        PEN_02 = pg.mkPen(controls.COLOR_PEN_YELLOW, width=3)
        PEN_03 = pg.mkPen(controls.COLOR_PEN_GREEN, width=3)
        PEN_04 = pg.mkPen(controls.COLOR_PEN_TURQUOISE, width=3)
        PEN_05 = pg.mkPen(controls.COLOR_PEN_PINK, width=3)

        self.curve_P_pump = HistoryChartCurve(
            capacity=capacity,
            linked_curve=self.pi_pres.plot(pen=PEN_01, name="P_pump"),
        )
        self.curve_P_1 = HistoryChartCurve(
            capacity=capacity,
            linked_curve=self.pi_pres.plot(pen=PEN_02, name="P_1"),
        )
        self.curve_P_2 = HistoryChartCurve(
            capacity=capacity,
            linked_curve=self.pi_pres.plot(pen=PEN_03, name="P_2"),
        )
        self.curve_P_3 = HistoryChartCurve(
            capacity=capacity,
            linked_curve=self.pi_pres.plot(pen=PEN_04, name="P_3"),
        )
        self.curve_P_4 = HistoryChartCurve(
            capacity=capacity,
            linked_curve=self.pi_pres.plot(pen=PEN_05, name="P_4"),
        )

        self.curves_pres = [
            self.curve_P_pump,
            self.curve_P_1,
            self.curve_P_2,
            self.curve_P_3,
            self.curve_P_4,
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
            "maximumWidth": controls.e8(6),
            "minimumWidth": controls.e8(6),
        }
        self.qlin_P_pump = QtWid.QLineEdit(**p)
        self.qlin_P_1 = QtWid.QLineEdit(**p)
        self.qlin_P_2 = QtWid.QLineEdit(**p)
        self.qlin_P_3 = QtWid.QLineEdit(**p)
        self.qlin_P_4 = QtWid.QLineEdit(**p)

        # fmt: off
        legend_1.grid.setHorizontalSpacing(6)
        legend_1.grid.addWidget(self.qlin_P_pump   , 0, 2)
        legend_1.grid.addWidget(QtWid.QLabel("bar"), 0, 3)
        legend_1.grid.addWidget(self.qlin_P_1      , 1, 2)
        legend_1.grid.addWidget(QtWid.QLabel("bar"), 1, 3)
        legend_1.grid.addWidget(self.qlin_P_2      , 2, 2)
        legend_1.grid.addWidget(QtWid.QLabel("bar"), 2, 3)
        legend_1.grid.addWidget(self.qlin_P_3      , 3, 2)
        legend_1.grid.addWidget(QtWid.QLabel("bar"), 3, 3)
        legend_1.grid.addWidget(self.qlin_P_4      , 4, 2)
        legend_1.grid.addWidget(QtWid.QLabel("bar"), 4, 3)
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
        self.qtxt_comments.setMinimumHeight(controls.e8(8))
        self.qtxt_comments.setMaximumWidth(controls.e8(26))
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

        p = {"alignment": QtCore.Qt.AlignmentFlag.AlignLeft}
        vbox_readings = QtWid.QVBoxLayout()
        vbox_readings.addWidget(qgrp_readings)
        vbox_readings.addWidget(qgrp_comments, **p)
        vbox_readings.addWidget(qgrp_charts, **p)

        grid_bot = QtWid.QGridLayout()
        grid_bot.addLayout(vbox_pump, 0, 0)
        grid_bot.addWidget(
            qgrp_protocol, 0, 1, QtCore.Qt.AlignmentFlag.AlignTop
        )
        grid_bot.addWidget(self.gw, 0, 2)
        grid_bot.addLayout(vbox_readings, 0, 3)
        grid_bot.setColumnStretch(0, 0)
        grid_bot.setColumnStretch(1, 0)
        grid_bot.setColumnStretch(2, 1)
        grid_bot.setColumnStretch(3, 0)

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

        self.grid_qdev.signal_DAQ_updated.connect(self.update_GUI)
        self.grid_qdev.signal_GUI_needs_update.connect(self.update_GUI)

        self.logger.signal_recording_started.connect(
            lambda filepath: self.qpbt_record.setText(
                f"Recording to file: {filepath}"
            )
        )
        self.logger.signal_recording_stopped.connect(
            lambda: self.qpbt_record.setText("Click to start recording to file")
        )

    # --------------------------------------------------------------------------
    #   Handle general controls
    # --------------------------------------------------------------------------

    def toggle_icons(self, event):
        self.icon_1.setVisible(not self.icon_1.isVisible())
        self.icon_2.setVisible(not self.icon_2.isVisible())

    @Slot()
    def update_wall_clock(self):
        cur_date_time = QtCore.QDateTime.currentDateTime()
        self.qlbl_cur_date_time.setText(
            f"{cur_date_time.toString('dd-MM-yyyy')}    "
            f"{cur_date_time.toString('HH:mm:ss')}"
        )

    @Slot()
    @Slot(int)
    def update_GUI(self, GUI_object=GUI_objects.ALL):
        # Shorthands
        grid = self.grid
        grid_qdev = self.grid_qdev
        pump = self.pump

        if GUI_object == GUI_objects.PROTO_POS:
            self.qpbt_proto_pos.setText(f"{int(grid.state.protocol_pos):d}")

        elif GUI_object == GUI_objects.PROTO_INFO:
            self.qlin_proto_name.setText(grid.state.protocol_name)

        else:
            self.qlbl_update_counter.setText(f"{grid_qdev.update_counter_DAQ}")
            self.qlbl_DAQ_rate.setText(
                f"DAQ: {grid_qdev.obtained_DAQ_rate_Hz:.1f} Hz"
            )
            self.qlbl_recording_time.setText(
                f"REC: {self.logger.pretty_elapsed()}"
                if self.logger.is_recording()
                else ""
            )

            self.qlin_P_pump.setText(f"{pump.state.actual_pressure:.3f}")
            self.qpbt_proto_pos.setText(f"{int(grid.state.protocol_pos):d}")
            self.qlin_P_1.setText(f"{grid.state.P_1_bar:.3f}")
            self.qlin_P_2.setText(f"{grid.state.P_2_bar:.3f}")
            self.qlin_P_3.setText(f"{grid.state.P_3_bar:.3f}")
            self.qlin_P_4.setText(f"{grid.state.P_4_bar:.3f}")

            # Don't allow uploading a protocol when the pump is still running
            self.qpbt_proto_upload.setEnabled(not pump.state.pump_is_running)

            if self.debug:
                tprint("update_charts")

            for curve in self.curves:
                curve.update()

    # --------------------------------------------------------------------------
    #   Handle protocol controls
    # --------------------------------------------------------------------------

    @Slot()
    def process_qpbt_proto_upload(self):
        # Extra safety check: Don't allow uploading a protocol when the pump is
        # still running
        if self.pump.state.pump_is_running:
            return

        # Get the folder that was last used to load in a protocol file
        last_used_folder = ""
        config_path = Path("config/protocol_folder.txt")
        if config_path.is_file():
            try:
                with config_path.open() as f:
                    last_used_folder = Path(f.readline().strip())
            except:
                pass  # Do not panic and remain silent

        # Open file navigator
        reply = QtWid.QFileDialog.getOpenFileName(
            self,
            "Upload protocol file",
            str(last_used_folder),
            "Protocol files (*.proto)",
        )

        if not reply[0]:
            # User pressed cancel
            return

        # Extract the full file path and file folder
        file_path = Path(reply[0])
        file_folder = file_path.parent

        # Save the last used folder to disk
        if not config_path.parent.is_dir():
            # Subfolder 'config/' does not exists yet. Create.
            try:
                config_path.parent.mkdir()
            except:
                pass  # Do not panic and remain silent

        try:
            # Write the config file
            config_path.write_text(str(file_folder))
        except:
            pass  # Do not panic and remain silent

        # Stop the `DAQ_function` running in the worker thread from sending and
        # receiving ASCII data containing pressure data. We are about to upload
        # a raw byte stream to the Arduino decoding a jetting protocol and it
        # must not be interferred.
        # We stop the ASCII stream in the `DAQ_function` in a hacky way by
        # temporarily letting it point to an empty function. It would be better
        # if we build support for "silencing" the DAQ function inside of the
        # `dvg_qdeviceio::Worker_DAQ()` class (future work perhaps).
        DAQ_function_backup = self.grid_qdev.worker_DAQ.DAQ_function

        def empty_DAQ_function():
            return True

        self.grid_qdev.worker_DAQ.DAQ_function = empty_DAQ_function

        # Wait a few DAQ iterations
        i = self.grid_qdev.update_counter_DAQ
        while self.grid_qdev.update_counter_DAQ <= i + 1:
            pass

        # Flush serial buffer
        self.grid.ser.flush()

        # Now we're ready to upload a new jetting protocol
        upload_protocol(self.grid, file_path)

        # Retrieve the name and total number of lines of the protocol currently
        # loaded into the Arduino
        self.grid.get_protocol_info()
        self.update_GUI(GUI_objects.PROTO_INFO)

        # Restore DAQ function
        self.grid_qdev.worker_DAQ.DAQ_function = DAQ_function_backup

    @Slot()
    def process_qpbt_proto_stop(self):
        if self.pump.is_alive:
            # Safely stop the pump first and only then stop the protocol and
            # close all valves. The `pump_qdev` will emit a signal once it has
            # reached standstill, which we will connect in `main.py` to the
            # `stop protocol` command.
            self.pump_qdev.send_pump_stop()
            self.grid_qdev.waiting_for_pump_standstill_to_stop_protocol = True
        else:
            # Pump is not alive, so it is safe to immediately close all valves.
            self.grid_qdev.send_stop_protocol()

    @Slot()
    def process_qpbt_proto_gotoline(self):
        user_str, user_ok = QtWid.QInputDialog.getText(
            self, "Go to protocol line", "Enter line number:"
        )
        if user_ok and not user_str == "":
            try:
                line_no = int(user_str)
            except (ValueError, TypeError):
                line_no = 1

            self.grid_qdev.send_gotoline_protocol(line_no)

    @Slot(int)
    def process_qpbtn_preset(self, preset_no: int):
        reply = QtWid.QMessageBox.question(
            self,
            "Confirmation",
            f"Do you want to load in preset {preset_no}?",
        )

        if reply == QtWid.QMessageBox.StandardButton.Yes:
            self.grid_qdev.send_load_preset(preset_no)
