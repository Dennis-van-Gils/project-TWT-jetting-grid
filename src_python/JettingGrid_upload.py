#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JettingGrid_upload.py

Manages uploading a jetting protocol to the Arduino.

TODO: Work-in-progress. This module works but is very fugly.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "31-03-2023"
__version__ = "1.0"
# pylint: disable=pointless-string-statement

import sys
import struct

from dvg_devices.Arduino_protocol_serial import Arduino

# ------------------------------------------------------------------------------
#   Point `P` in the protocol coordinate system (PCS)
# -----------------------------------------------------------------------------

# Constants
PCS_X_MIN = -7
PCS_Y_MIN = -7


class P:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def pack_into_byte(self):
        return ((self.x - PCS_X_MIN) << 4) | ((self.y - PCS_Y_MIN) & 0xF)


# ------------------------------------------------------------------------------
#   upload_protocol()
# -----------------------------------------------------------------------------


def upload_protocol(grid: Arduino):
    print("Uploading protocol")
    print("------------------")

    # Read in protocol file from disk
    filename = "proto_example.txt"
    with open(file=filename, mode="r", encoding="utf8") as f:
        lines = [line.rstrip() for line in f]

    # Find DATA section
    data_line_idx = None
    for line_idx, line in enumerate(lines):
        if line == "[DATA]":
            data_line_idx = line_idx + 1
            break

    if data_line_idx is None:
        print("No [DATA] section found")
        sys.exit()  # TODO: Do not hard exit, but gracefully notify user

    lines = lines[data_line_idx:]
    N_lines = len(lines)

    # Enter the upload state
    grid.set_write_termination("\n")
    if not grid.write("upload"):
        # TODO: Show message box referring to error in terminal
        return

    # Stage 0: Send via ASCII the name of the protocol program.
    # --------------------------------------------------------------------------
    success, ans = grid.query(filename)
    if not success:
        # TODO: Show message box referring to error in terminal
        return

    print(ans)

    # Stage 1: Send via ASCII the total number of protocol lines that follow.
    # --------------------------------------------------------------------------
    success, ans = grid.query(f"{N_lines}")
    if not success:
        # TODO: Show message box referring to error in terminal
        return

    if ans[:5] == "ERROR":
        # TODO: Show error message box
        print(ans)
        return

    # Stage 2: Send via binary the protocol program line-by-line. Each line is
    # termined by an end-of-line (EOL) sentinel. Two EOL sentinels directly send
    # after each other signal the end-of-program (EOP).
    # --------------------------------------------------------------------------
    grid.set_write_termination(bytes((0xFF, 0xFF, 0xFF)))  # EOL sentinel

    for idx_line, line in enumerate(lines):
        print(f"\rLine {idx_line + 1} of {N_lines}", end="")
        fields = line.split("\t")
        duration = int(fields[0])

        # Build raw byte stream
        raw = bytearray(struct.pack(">H", duration))  # Time duration [ms]
        str_points = fields[1:]
        for str_point in str_points:
            str_x, str_y = str_point.split(",")
            raw.append(P(int(str_x), int(str_y)).pack_into_byte())

        # Send out raw byte stream
        grid.write(raw)

    # Send EOP sentinel
    grid.write(b"")
    print("")

    # Check for success
    success, ans = grid.readline()
    if not success:
        # TODO: Show message box referring to error in terminal
        grid.set_write_termination("\n")
        return

    if ans[:5] == "ERROR":
        # TODO: Show error message box
        pass
    elif ans[:16] == "EXECUTION HALTED":
        # TODO: Show error message box
        # This error has two lines to be read over serial
        print(ans)
        _, ans = grid.readline()

    print(ans)

    # Restore ASCII communication
    grid.set_write_termination("\n")


# ------------------------------------------------------------------------------
#   Main
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    grid = Arduino()
    grid.auto_connect()

    upload_protocol(grid)
