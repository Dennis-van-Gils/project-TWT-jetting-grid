#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import serial
import time

from CRC_check import CRC_check
import HVL_Registers as hvl


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
        for byte in self.byte_msg:
            msg += f"{byte:02x} "

        return msg


if __name__ == "__main__":
    # Default for RTU is 9600-8N1
    ser = serial.Serial(
        port="COM12",
        baudrate=9600,
        bytesize=8,
        parity="N",
        stopbits=1,
    )

    rtu = RTU_single_reg(func=0x06, addr_hi=0x00, addr_lo=0xE8)
    rtu.set_data(350)
    rtu.compile()
    print(rtu)

    ser.write(rtu.byte_msg)
    time.sleep(0.1)
    ans = ser.read_all()

    if ans is not None:
        for b in ans:
            print(f"{b:02x} ", end="")
    print("")

    # Read baudrate
    cmd = bytearray([0x01, 0x03, 0x01, 0x0E, 0x00, 0x01])
    cmd.extend(CRC_check(cmd))

    ser.write(cmd)
    time.sleep(0.1)
    ans = ser.read_all()

    if ans is not None:
        for b in ans:
            print(f"{b:02x} ", end="")
            # print(b, end="")
