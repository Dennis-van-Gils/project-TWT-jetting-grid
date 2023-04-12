#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JettingGrid_Arduino.py

Manages low-level serial communication with the Jetting Grid Arduino
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "12-04-2023"
__version__ = "1.0"

from datetime import datetime

import numpy as np

from dvg_debug_functions import dprint, print_fancy_traceback as pft
from dvg_devices.Arduino_protocol_serial import Arduino


# ------------------------------------------------------------------------------
#   current_date_time_strings
# ------------------------------------------------------------------------------


def current_date_time_strings():
    cur_date_time = datetime.now()
    return (
        cur_date_time.strftime("%d-%m-%Y"),  # Date
        cur_date_time.strftime("%H:%M:%S"),  # Time
    )


# ------------------------------------------------------------------------------
#   JettingGrid_Arduino
# ------------------------------------------------------------------------------


class JettingGrid_Arduino(Arduino):
    class State(object):
        """Container for the process and measurement variables"""

        def __init__(self):
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

    # --------------------------------------------------------------------------
    #   JettingGrid_Arduino
    # --------------------------------------------------------------------------

    def __init__(self, name="Ard", connect_to_specific_ID="Jetting Grid"):
        super().__init__(
            name=name,
            connect_to_specific_ID=connect_to_specific_ID,
        )
        self.serial_settings["baudrate"] = 115200

        # Container for the process and measurement variables
        self.state = self.State()

    # --------------------------------------------------------------------------
    #   perform_DAQ
    # --------------------------------------------------------------------------

    def perform_DAQ(self) -> bool:
        """Returns True when successful, False otherwise."""

        # Query the Arduino for its state
        success, reply = self.query_ascii_values("?", delimiter="\t")
        if not success:
            str_cur_date, str_cur_time = current_date_time_strings()
            dprint(
                f"'{self.name}' reports IOError @ {str_cur_date} {str_cur_time}"
            )
            return False

        # Parse readings into separate state variables
        try:
            # pylint: disable=unbalanced-tuple-unpacking
            (
                self.state.protocol_pos,
                self.state.P_1_mA,
                self.state.P_2_mA,
                self.state.P_3_mA,
                self.state.P_4_mA,
                self.state.P_1_bar,
                self.state.P_2_bar,
                self.state.P_3_bar,
                self.state.P_4_bar,
            ) = reply
            # pylint: enable=unbalanced-tuple-unpacking
        except Exception as err:
            str_cur_date, str_cur_time = current_date_time_strings()
            pft(err)
            dprint(
                f"'{self.name}' reports IOError @ {str_cur_date} {str_cur_time}"
            )
            return False

        return True

    # --------------------------------------------------------------------------
    #   Misc. methods
    # --------------------------------------------------------------------------

    def play_protocol(self) -> bool:
        """Play the protocol and automatically actuate valves over time.

        Returns: True if successful, False otherwise.
        """
        return self.write("play")

    def stop_protocol(self) -> bool:
        """Stop the protocol and close all valves immediately. The protocol
        position at the moment of pause will get updated in the `state` member.

        Returns: True if successful, False otherwise.
        """
        success, reply = self.query("stop")
        if success:
            try:
                num = int(reply)
            except (TypeError, ValueError) as err:
                pft(err)
            else:
                # All successful
                self.state.protocol_pos = num
                return True

        return False

    def pause_protocol(self) -> bool:
        """Pause the protocol keeping the last actuated states of the valves.
        The protocol position at the moment of stop will get updated in the
        `state` member.

        Returns: True if successful, False otherwise.
        """
        success, reply = self.query("pause")
        if success:
            try:
                num = int(reply)
            except (TypeError, ValueError) as err:
                pft(err)
            else:
                # All successful
                self.state.protocol_pos = num
                return True

        return False
