#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JettingGrid_upload.py

Manages uploading a jetting protocol to the Arduino
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-TWT-jetting-grid"
__date__ = "30-03-2023"
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
    def __init__(self, x_=0, y_=0):
        # TODO: Rethink default value to match end sentinel
        self.x = x_
        self.y = y_

    def pack_into_byte(self):
        return ((self.x - PCS_X_MIN) << 4) | ((self.y - PCS_Y_MIN) & 0xF)


# ------------------------------------------------------------------------------
#   upload_protocol()
# -----------------------------------------------------------------------------


def upload_protocol(grid: Arduino):
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
        sys.exit()
    lines = lines[data_line_idx:]

    grid.set_write_termination("\n")

    success, ans = grid.query("load")
    print(ans)
    success, ans = grid.query("OpenSimplex noise")
    print(ans)
    success, ans = grid.query(f"{len(lines)}")
    print(ans)

    if ans == "Loading stage 1: Success":
        # Prepare binary data stream
        grid.set_write_termination(bytes((0xFF, 0xFF, 0xFF)))  # EOL

        cnt = 0
        found_data_section = False
        for line in lines:
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

            """
            # Force a time-out for debug testing
            cnt += 1
            if cnt == 30:
                time.sleep(4)
            """

        ### Send EOP
        grid.write(b"")

        print("Last line send")

        ### Check for success
        success, ans = grid.readline()
        if ans == "Loading stage 2: Success":
            print("Success")
        else:
            print(ans)

    else:
        print(ans)

    ### Catch "State: Idling..."
    # success, ans = grid.readline()
    # print(ans)

    ### Restore ASCII communication
    grid.set_write_termination("\n")


# ------------------------------------------------------------------------------
#   Main
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    grid = Arduino()
    grid.auto_connect()
    # grid.ser.timeout = 4
    # grid.ser.write_timeout = 4

    upload_protocol(grid)
