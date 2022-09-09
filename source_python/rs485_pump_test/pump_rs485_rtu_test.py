#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import serial
import time

from CRC_check import CRC_check


class RTU_single_reg:
    def __init__(self, slave_addr=0x01, func=0x00, addr_hi=0x00, addr_lo=0x00):
        self.slave_addr = slave_addr
        self.func = func
        self.addr_hi = addr_hi
        self.addr_lo = addr_lo
        self.data_hi = 0x00
        self.data_lo = 0x00
        self.crc_hi = 0x00
        self.crc_lo = 0x00

        self.byte_msg = bytearray(8)

    def set_data(self, val):
        self.data_hi = (val & 0xFF00) >> 8
        self.data_lo = val & 0x00FF

    def compile(self):
        self.byte_msg[0] = self.slave_addr
        self.byte_msg[1] = self.func
        self.byte_msg[2] = self.addr_hi
        self.byte_msg[3] = self.addr_lo
        self.byte_msg[4] = self.data_hi
        self.byte_msg[5] = self.data_lo

        self.crc_hi, self.crc_lo = CRC_check(self.byte_msg[:6])
        self.byte_msg[6] = self.crc_hi
        self.byte_msg[7] = self.crc_lo

        return self.byte_msg

    def __str__(self):
        msg = ""
        for b in self.byte_msg:
            msg += "%02x " % b

        return msg


# Default 9600-8N1
ser = serial.Serial("COM12")

rtu = RTU_single_reg(func=0x06, addr_hi=0x00, addr_lo=0xE8)
rtu.set_data(350)
rtu.compile()
print(rtu)

ser.write(rtu.byte_msg)
time.sleep(0.1)
ans = ser.read_all()

for b in ans:
    print("%02x " % b, end="")
