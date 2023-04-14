#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JettingGrid_Arduino.py

Manages low-level serial communication with the Jetting Grid Arduino
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "14-04-2023"
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
            self.protocol_name = ""
            self.protocol_N_lines = 0
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

    def _protocol_query_fun(self, query_cmd: str) -> bool:
        """Helper function to send a query command to the Arduino involving the
        protocol controls 'pause/stop/rewind/prevline/nextline'. The protocol
        position is returned by the query and will get updated in the `state`
        member.
        Returns: True if successful, False otherwise.
        """
        success, reply = self.query(query_cmd)
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

    def play_protocol(self) -> bool:
        """Play the protocol and automatically actuate valves over time.
        Returns: True if successful, False otherwise.
        """
        return self.write("play")

    def stop_protocol(self) -> bool:
        """Stop the protocol and immediately close all valves.

        WARNING: This method is ignorant of whether the jetting pump is running
        or not. Closing all valves suddenly while the pump is running can damage
        the system.

        Returns: True if successful, False otherwise.
        """
        return self._protocol_query_fun("stop")

    def pause_protocol(self) -> bool:
        """Pause the protocol keeping the last actuated states of the valves.
        Returns: True if successful, False otherwise.
        """
        return self._protocol_query_fun("pause")

    def rewind_protocol(self) -> bool:
        """Rewind the protocol and immediately actuate valves.
        Returns: True if successful, False otherwise.
        """
        return self._protocol_query_fun("goto 1")

    def prevline_protocol(self) -> bool:
        """Go to the previous line of the protocol and immediately actuate
        valves.
        Returns: True if successful, False otherwise.
        """
        return self._protocol_query_fun(",")

    def nextline_protocol(self) -> bool:
        """Go to the next line of the protocol and immediately actuate valves.
        Returns: True if successful, False otherwise.
        """
        return self._protocol_query_fun(".")

    def gotoline_protocol(self, line_no: int) -> bool:
        """Go to the given line number of the protocol and immediately actuate
        valves.
        Returns: True if successful, False otherwise.
        """
        try:
            idx_line = int(line_no)
        except (TypeError, ValueError):
            idx_line = 1

        return self._protocol_query_fun(f"goto {idx_line:d}")

    def load_preset(self, preset_no: int) -> bool:
        """Load in a protocol preset:
            0: Open all valves
            1: Walk over all valves
            2: Walk over all manifolds
            3: Alternating checkerboard
            4: Alternating even/odd valves

        The name and total number of lines of the protocol will get updated in
        members `state.protocol_name` and `state.protocol_N_lines`.

        Returns: True if successful, False otherwise.
        """
        try:
            idx_preset = int(preset_no)
        except (TypeError, ValueError):
            idx_preset = 0

        # Only presets 0 to 4 exist. Check user input.
        IDX_PRESET_MAX = 4
        if not idx_preset in range(IDX_PRESET_MAX + 1):
            idx_preset = 0

        success = self.write(f"preset{idx_preset:d}")
        success &= self.get_protocol_info()

        return success

    def get_protocol_info(self) -> bool:
        """Get the name and total number of lines of the protocol currently
        loaded into the Arduino, and write them into members
        `state.protocol_name` and `state.protocol_N_lines`.
        Returns: True if successful, False otherwise.
        """
        success, reply = self.query("p?")

        if not success:
            return False

        try:
            info1, info2 = reply.split("\t")
            self.state.protocol_name = info1
            self.state.protocol_N_lines = int(info2)
        except Exception as err:
            str_cur_date, str_cur_time = current_date_time_strings()
            pft(err)
            dprint(
                f"'{self.name}' reports IOError @ {str_cur_date} {str_cur_time}"
            )
            return False

        return True
