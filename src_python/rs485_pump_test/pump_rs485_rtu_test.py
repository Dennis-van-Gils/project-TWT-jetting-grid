#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from time import perf_counter

from XylemHydrovarHVL_protocol_RTU import XylemHydrovarHVL, HVL_Mode

if __name__ == "__main__":
    # Path to the textfile containing the (last used) serial port
    PATH_PORT = "config/port_Hydrovar.txt"

    hvl = XylemHydrovarHVL(connect_to_modbus_slave_address=0x01)
    hvl.serial_settings = {
        "baudrate": 115200,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
        "timeout": 0.2,
        "write_timeout": 0.2,
    }
    hvl._query_wait_time = 0.05

    if hvl.auto_connect(PATH_PORT):
        hvl.begin()
    else:
        sys.exit(0)

    hvl.set_error_reset(False)
    hvl.use_digital_required_value_1()

    hvl.set_mode(HVL_Mode.CONTROLLER)
    hvl.read_actual_value()

    # hvl.set_required_pressure(1)
    # hvl.read_required_pressure()

    hvl.read_diagnostic_values()

    tick = perf_counter()
    N = 100
    for i in range(N):
        hvl.read_diagnostic_values()

    print(f"time per eval: {(perf_counter() - tick)*1000/N:.0f} ms")
