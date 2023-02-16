#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from XylemHydrovarHVL_protocol_RTU import XylemHydrovarHVL

if __name__ == "__main__":
    # Path to the textfile containing the (last used) serial port
    PATH_PORT = "config/port_Hydrovar.txt"

    hvl = XylemHydrovarHVL(connect_to_modbus_slave_address=0x01)
    hvl.serial_settings = {
        "baudrate": 9600,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
        "timeout": 0.2,
        "write_timeout": 0.2,
    }

    if hvl.auto_connect(PATH_PORT):
        hvl.read_actual_pressure()
        hvl.read_required_pressure()
