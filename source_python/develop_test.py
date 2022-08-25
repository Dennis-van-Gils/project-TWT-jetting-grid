#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# TIPS: http://dabeaz.blogspot.com/2010/01/few-useful-bytearray-tricks.html

import struct

from dvg_devices.Arduino_protocol_serial import Arduino

PCS_X_MIN = -7
PCS_Y_MIN = -7

class P:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
    
    def pack_into_byte(self):
        #print("(%d,%d)" % (self.x, self.y))
        return (((self.x - PCS_X_MIN) << 4) | ((self.y - PCS_Y_MIN) & 0xf))

if 0:
    line = (P(-7,-7), P(-7, 7), P(7, -7), P(-7, -7), P(0, 0))
else:
    line = list()
    for x in range(-7, 8):
        for y in range(-7, 8):
            if (x + y) & 1:
                line.append(P(x, y))

ard = Arduino()
ard.auto_connect()

print(ard.query("load"))

# Prepare binary data stream

ard.set_write_termination(bytes((0xff, 0xff, 0xff, 0xff)))   # EOL

### First line

raw = bytearray(struct.pack(">L", 255))  # Time duration
for p in line:  # List of PCS points
    raw.append(p.pack_into_byte())

ard.write(raw)
success, ans = ard.readline()
print(ans)

### Second line

raw = bytearray(struct.pack(">L", 65535))  # Time duration
line = (P(0, 1), P(1, 0), P(0, -1), P(-1, 0))
for p in line:  # List of PCS points
    raw.append(p.pack_into_byte())

ard.write(raw)
success, ans = ard.readline()
print(ans)

### Send EOP

ard.write(b"")
success, ans = ard.readline()
print(ans)

### Restore

ard.set_write_termination("\n")