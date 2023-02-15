#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Modbus RTU protocol (RS485) function library for a Xylem Hydrovar HVL
variable speed drive (VSD) controller.

This module supports just one slave device on the Modbus, not multiple. With
just one slave device the communication handling gets way simpler as we don't
have to figure out which reply message belongs to which slave device in case we
would have multiple slave devices. Also, the query and reply parsing can now be
handled inside of a single function, instead of having to handle this
asynchronously across multiple functions.

Reference documents:
(1) Hydrovar HVL 2.015 - 4.220 Modbus Protocol & Parameters
------------------------------------------------------------------------
Function codes:
    0x03: READ COMMAND, read holding registers
    0x06: WRITE COMMAND, write single register
    0x10: WRITE COMMAND, write multiple contiguous registers
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/python-dvg-devices"
__date__ = "15-02-2023"
__version__ = "1.0.0"

import os
from typing import Tuple, Union
from pathlib import Path
from enum import Enum, IntEnum

from dvg_devices.BaseDevice import SerialDevice
from CRC_check import CRC_check


def pretty_format_hex(byte_msg: bytes) -> str:
    msg = ""
    for byte in byte_msg:
        msg += f"{byte:02x} "
    return msg


# ------------------------------------------------------------------------------
#   Enumerations
# ------------------------------------------------------------------------------


class HVL_FuncCode(Enum):
    # Implemented:
    READ = 0x03  # Read the binary contents of registers
    WRITE = 0x06  # Write a value into a single register

    # Not implemented:
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


# ------------------------------------------------------------------------------
#   HVL_Register
# ------------------------------------------------------------------------------


class HVL_Register:
    def __init__(
        self,
        address: int,
        datum_type: HVL_DType,
        menu_index: str = "",
    ):
        self.address = address  # Modbus address as taken from Table 5, ref (1)
        self.datum_type = datum_type
        self.menu_index = menu_index


# ------------------------------------------------------------------------------
#   XylemHydrovarHVL
# ------------------------------------------------------------------------------


class XylemHydrovarHVL(SerialDevice):
    class State:
        """Container for the process and measurement variables."""

        pass

    def __init__(
        self,
        name: str = "HVL",
        long_name: str = "Xylem Hydrovar HVL variable speed drive",
        # path_config: str = (os.getcwd() + "/config/settings_Hydrovar.txt"),
        connect_to_modbus_slave_address: int = 0x01,
    ):
        super().__init__(name=name, long_name=long_name)

        # Default for RTU is 9600-8N1
        self.serial_settings = {
            "baudrate": 9600,
            "bytesize": 8,
            "parity": "N",
            "stopbits": 1,
            "timeout": 0.2,
            "write_timeout": 0.2,
        }
        self.set_read_termination("")
        self.set_write_termination("")

        self.set_ID_validation_query(
            ID_validation_query=self.ID_validation_query,
            valid_ID_broad=True,
            valid_ID_specific=connect_to_modbus_slave_address,
        )

        # Container for the process and measurement variables
        self.state = self.State()

        # Modbus slave address of the device (P1205)
        self.modbus_slave_address = connect_to_modbus_slave_address

        # Location of the configuration file
        # self.path_config = Path(path_config)

    # --------------------------------------------------------------------------
    #   ID_validation_query
    # --------------------------------------------------------------------------

    def ID_validation_query(self) -> Tuple[bool, Union[int, None]]:
        success = self.query_modbus_slave_address()
        return success, self.modbus_slave_address

    def construct_RTU_read_command(self, register: HVL_Register) -> bytes:
        """Construct a full byte array including CRC check to send over to the
        Hydrovar controller"""
        # fmt: off
        byte_msg = bytearray(8)
        byte_msg[0] = self.modbus_slave_address
        byte_msg[1] = HVL_FuncCode.READ.value
        byte_msg[2] = (register.address & 0xFF00) >> 8  # address HI
        byte_msg[3] = register.address & 0x00FF         # address LO
        byte_msg[4] = 0x00                              # no. of points HI
        byte_msg[5] = 0x01                              # no. of points LO
        byte_msg[6:] = CRC_check(byte_msg[:6])
        # fmt: on
        print(pretty_format_hex(byte_msg))
        return byte_msg

    def construct_RTU_write_command(
        self, register: HVL_Register, value: int
    ) -> bytes:
        """Construct a full byte array including CRC check to send over to the
        Hydrovar controller"""
        # fmt: off
        byte_msg = bytearray(8)
        byte_msg[0] = self.modbus_slave_address
        byte_msg[1] = HVL_FuncCode.WRITE.value
        byte_msg[2] = (register.address & 0xFF00) >> 8  # address HI
        byte_msg[3] = register.address & 0x00FF         # address LO
        byte_msg[4] = (value & 0xFF00) >> 8             # data HI
        byte_msg[5] = value & 0x00FF                    # data LO
        byte_msg[6:] = CRC_check(byte_msg[:6])
        # fmt: on
        print(pretty_format_hex(byte_msg))
        return byte_msg

    # --------------------------------------------------------------------------
    #
    # --------------------------------------------------------------------------

    def turn_on_pump(self) -> bool:
        byte_msg = self.construct_RTU_write_command(HVL_STOP_START, 1)
        success, reply = self.query(byte_msg, returns_ascii=False)

        # TODO: make more intelligent
        if isinstance(reply, bytes):
            print(pretty_format_hex(reply))
            print(f"DEC VALUE: {int(reply[4:6].hex(), 16):d}")

        return success

    def turn_off_pump(self) -> bool:
        byte_msg = self.construct_RTU_write_command(HVL_STOP_START, 0)
        success, reply = self.query(byte_msg, returns_ascii=False)

        # TODO: make more intelligent
        if isinstance(reply, bytes):
            print(pretty_format_hex(reply))
            print(f"DEC VALUE: {int(reply[4:6].hex(), 16):d}")

        return success

    def query_actual_value(self) -> bool:
        byte_msg = self.construct_RTU_read_command(HVL_ACTUAL_VALUE)
        success, reply = self.query(byte_msg, returns_ascii=False)

        # TODO: make more intelligent
        if isinstance(reply, bytes):
            print(pretty_format_hex(reply))
            print(f"DEC VALUE: {int(reply[3:5].hex(), 16):d}")

        return success

    # --------------------------------------------------------------------------
    #   query_modbus_slave_address
    # --------------------------------------------------------------------------

    def query_modbus_slave_address(self) -> bool:
        """Query the Modbus slave address of the device (P1205).

        Returns: True if successful, False otherwise.
        """
        byte_msg = self.construct_RTU_read_command(HVL_ADDRESS)
        success, reply = self.query(byte_msg, returns_ascii=False)

        # TODO: make more intelligent
        if isinstance(reply, bytes):
            print(pretty_format_hex(reply))

        return success


# List of registers (incomplete list, just the bare essentials)
# fmt: off
HVL_STOP_START    = HVL_Register(0x0031, HVL_DType.U08, "")
HVL_ACTUAL_VALUE  = HVL_Register(0x0032, HVL_DType.S16, "")
HVL_OUTPUT_FREQ   = HVL_Register(0x0033, HVL_DType.S16, "P46")
HVL_EFF_REQ_VAL   = HVL_Register(0x0037, HVL_DType.U16, "P03")
HVL_START_VALUE   = HVL_Register(0x0038, HVL_DType.U08, "P04")
HVL_ENABLE_DEVICE = HVL_Register(0x0061, HVL_DType.U08, "P24")
HVL_ADDRESS       = HVL_Register(0x010d, HVL_DType.U08, "P1205")

# Diagnostics
HVL_TEMP_INVERTER = HVL_Register(0x0085, HVL_DType.S08, "P43")
HVL_CURR_INVERTER = HVL_Register(0x0087, HVL_DType.U16, "P44")
HVL_VOLT_INVERTER = HVL_Register(0x0088, HVL_DType.U16, "P45")
HVL_ERROR_RESET   = HVL_Register(0x00d3, HVL_DType.U08, "P615")

# Special status bits
HVL_ERRORS_H3     = HVL_Register(0x012d, HVL_DType.B2 , "")
HVL_DEV_STATUS_H4 = HVL_Register(0x01c1, HVL_DType.B1 , "")
# fmt: on
