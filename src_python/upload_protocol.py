#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# TIPS: http://dabeaz.blogspot.com/2010/01/few-useful-bytearray-tricks.html
# pylint: disable=pointless-string-statement

import sys
import struct
import time

from dvg_devices.Arduino_protocol_serial import Arduino

PCS_X_MIN = -7
PCS_Y_MIN = -7


class P:
    def __init__(self, x_=0, y_=0):
        # TODO: Rethink default value to match end sentinel
        self.x = x_
        self.y = y_

    def pack_into_byte(self):
        # print("(%d,%d)" % (self.x, self.y))
        return ((self.x - PCS_X_MIN) << 4) | ((self.y - PCS_Y_MIN) & 0xF)


# ------------------------------------------------------------------------------
#   Send out protocol
# -----------------------------------------------------------------------------

ard = Arduino()
ard.auto_connect()
# ard.ser.timeout = 4
# ard.ser.write_timeout = 4


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

ard.set_write_termination("\n")

success, ans = ard.query("load")
print(ans)
success, ans = ard.query("OpenSimplex noise")
print(ans)
success, ans = ard.query(f"{len(lines)}")
print(ans)

if ans == "Loading stage 1: Success":
    # Prepare binary data stream
    ard.set_write_termination(bytes((0xFF, 0xFF, 0xFF)))  # EOL

    cnt = 0
    found_data_section = False
    for line in lines:
        fields = line.split("\t")
        duration = int(fields[0])

        # Raw byte stream
        raw = bytearray(struct.pack(">H", duration))  # Time duration [ms]
        # raw = bytearray(struct.pack(">H", 50))  # Time duration [ms]

        str_points = fields[1:]
        for str_point in str_points:
            str_x, str_y = str_point.split(",")
            raw.append(P(int(str_x), int(str_y)).pack_into_byte())

        ard.write(raw)

        """
        # Force a time-out
        cnt += 1
        if cnt == 30:
            time.sleep(4)
        """

    ### Send EOP
    ard.write(b"")

    print("Last line send")

    ### Check for success
    success, ans = ard.readline()
    if ans == "Loading stage 2: Success":
        print("Success")
    else:
        print(ans)

else:
    print(ans)

### Catch "State: Idling..."
# success, ans = ard.readline()
# print(ans)

### Restore ASCII communication
ard.set_write_termination("\n")
