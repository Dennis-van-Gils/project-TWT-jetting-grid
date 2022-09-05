#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# TIPS: http://dabeaz.blogspot.com/2010/01/few-useful-bytearray-tricks.html
# pylint: disable=pointless-string-statement

import struct

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


if 0:
    line = (P(-7, -7), P(-7, 7), P(7, -7), P(-7, -7), P(0, 0))
else:
    line = []
    for x in range(-7, 8):
        for y in range(-7, 8):
            if (x + y) & 1:
                line.append(P(x, y))

# ------------------------------------------------------------------------------
#   Send out protocol
# -----------------------------------------------------------------------------

ard = Arduino()
ard.auto_connect()

print(ard.query("load"))

# Prepare binary data stream
ard.set_write_termination(bytes((0xFF, 0xFF, 0xFF)))  # EOL

# Read in protocol file from disk
filename = "randomfiring_testpattern.txt"
with open(file=filename, mode="r", encoding="utf8") as f:
    lines = [line.rstrip() for line in f]

for line in lines:
    fields = line.split("\t")
    duration = float(fields[0])

    # Raw byte stream
    # raw = bytearray(struct.pack(">H", duration)) # Time duration [ms]
    raw = bytearray(struct.pack(">H", 500))  # Time duration [ms]

    str_points = fields[1:]
    for str_point in str_points:
        str_x, str_y = str_point.split(",")
        raw.append(P(int(str_x), int(str_y)).pack_into_byte())

    ard.write(raw)
    success, ans = ard.readline()
    # print(ans)
    success, ans = ard.readline()
    # print(ans)

### Send EOP
ard.write(b"")
success, ans = ard.readline()
print(ans)

### Restore ASCII communication
ard.set_write_termination("\n")

"""
### First line
raw = bytearray(struct.pack(">H", 2000))  # Time duration
for p in line:  # List of PCS points
    raw.append(p.pack_into_byte())

ard.write(raw)
success, ans = ard.readline()
print(ans)
success, ans = ard.readline()
print(ans)

### Second line
raw = bytearray(struct.pack(">H", 2000))  # Time duration
line = (P(0, 1), P(1, 0), P(0, -1), P(-1, 0))
for p in line:  # List of PCS points
    raw.append(p.pack_into_byte())

ard.write(raw)
success, ans = ard.readline()
print(ans)
success, ans = ard.readline()
print(ans)

### Send EOP
ard.write(b"")
success, ans = ard.readline()
print(ans)

### Restore ASCII communication
ard.set_write_termination("\n")
"""