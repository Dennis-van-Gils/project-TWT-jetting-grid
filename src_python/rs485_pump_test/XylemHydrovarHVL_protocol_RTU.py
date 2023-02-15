#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notes on cryptic manual "HVL 2.015 - 4.220 Modbus Protocol & Parameters"
------------------------------------------------------------------------

Function codes:
    0x03: READ COMMAND, read holding registers
    0x06: WRITE COMMAND, write single register
    0x10: WRITE COMMAND, write multiple contiguous registers
"""

import os
from enum import Enum, IntEnum

from dvg_devices.BaseDevice import SerialDevice


# Xylem Hydrovar HVL variable speed drive (VSD)
class XylemHydrovarHVL(SerialDevice):
    class State:
        """Container for the process and measurement variables."""

        pass

    def __init__(
        self,
        name: str = "HVL",
        long_name: str = "Xylem Hydrovar HVL variable speed drive",
        path_config: str = (os.getcwd() + "/config/settings_Hydrovar.txt"),
    ):
        super().__init__(name=name, long_name=long_name)


class HVL_FuncCode(Enum):
    READ = 0x03  # Read the binary contents of registers
    WRITE = 0x06  # Write a value into a single register
    WRITE_CONT = 0x10  # Write values into a block of contiguous registers


class HVL_DType(IntEnum):
    U08 = 0
    U16 = 1
    U32 = 2
    S08 = 3
    S16 = 4
    B0 = 5  # 8 bits bitmap
    B1 = 6  # 16 bits bitmap
    B2 = 7  # 32 bits bitmap


class HVL_Register:
    def __init__(self, modbus_address: int, datum_type: HVL_DType):
        self.modbus_address = modbus_address
        self.datum_type = datum_type


# List of registers and corresponding data type
# fmt: off
HVL_STOP_START    = HVL_Register(0x31, HVL_DType.U08)
HVL_ACTUAL_VALUE  = HVL_Register(0x32, HVL_DType.S16)
HVL_OUTPUT_FREQ   = HVL_Register(0x33, HVL_DType.S16)
HVL_EFF_REQ_VAL   = HVL_Register(0x37, HVL_DType.U16)
HVL_START_VALUE   = HVL_Register(0x38, HVL_DType.U08)
HVL_ENABLE_DEVICE = HVL_Register(0x61, HVL_DType.U08)

# Diagnostics
HVL_TEMP_INVERTER = HVL_Register(0x85, HVL_DType.S08)
HVL_CURR_INVERTER = HVL_Register(0x87, HVL_DType.U16)
HVL_VOLT_INVERTER = HVL_Register(0x88, HVL_DType.U16)
HVL_ERROR_RESET   = HVL_Register(0xd3, HVL_DType.U08)

# Special status bits
HVL_ERRORS_H3     = HVL_Register(0x012d, HVL_DType.B2)
HVL_DEV_STATUS_H4 = HVL_Register(0x01c1, HVL_DType.B1)
# fmt: on
