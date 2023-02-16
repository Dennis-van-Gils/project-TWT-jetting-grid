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
(1) Hydrovar HVL 2.015 - 4.220 | Modbus Protocol & Parameters
    HVL Software Version: 2.10, 2.20
    cod. 001085110 rev.B ed. 01/2018
(2) Hydrovar HVL 2.015 - 4.220 | Handleiding voor installatie, bediening en
    onderhoud
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/python-dvg-devices"
__date__ = "15-02-2023"
__version__ = "1.0.0"
# pylint: disable=invalid-name

from typing import Tuple, Union
from enum import IntEnum

import numpy as np

from dvg_debug_functions import print_fancy_traceback as pft
from dvg_devices.BaseDevice import SerialDevice
from crc import crc16


def pretty_format_hex(byte_msg: bytes) -> str:
    msg = ""
    for byte in byte_msg:
        msg += f"{byte:02x} "
    return msg


# ------------------------------------------------------------------------------
#   Enumerations
# ------------------------------------------------------------------------------


class HVL_FuncCode(IntEnum):
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


# List of registers (incomplete list, just the bare necessities)
# fmt: off
HVLREG_STOP_START    = HVL_Register(0x0031, HVL_DType.U08, "")      # RW
HVLREG_ACTUAL_VALUE  = HVL_Register(0x0032, HVL_DType.S16, "")      # R
HVLREG_OUTPUT_FREQ   = HVL_Register(0x0033, HVL_DType.S16, "P46")   # R
HVLREG_EFF_REQ_VAL   = HVL_Register(0x0037, HVL_DType.U16, "P03")   # R
HVLREG_START_VALUE   = HVL_Register(0x0038, HVL_DType.U08, "P04")   # RW
HVLREG_ENABLE_DEVICE = HVL_Register(0x0061, HVL_DType.U08, "P24")   # RW
HVLREG_ADDRESS       = HVL_Register(0x010d, HVL_DType.U08, "P1205") # RW

# Pressure setpoint
HVLREG_C_REQ_VAL_1   = HVL_Register(0x00e5, HVL_DType.U08, "P805")  # RW
HVLREG_SW_REQ_VAL    = HVL_Register(0x00e7, HVL_DType.U08, "P815")  # RW
HVLREG_REQ_VAL_1     = HVL_Register(0x00e8, HVL_DType.U16, "P820")  # RW

# Diagnostics
HVLREG_TEMP_INVERTER = HVL_Register(0x0085, HVL_DType.S08, "P43")   # R
HVLREG_CURR_INVERTER = HVL_Register(0x0087, HVL_DType.U16, "P44")   # R
HVLREG_VOLT_INVERTER = HVL_Register(0x0088, HVL_DType.U16, "P45")   # R
HVLREG_ERROR_RESET   = HVL_Register(0x00d3, HVL_DType.U08, "P615")  # RW

# Special status bits
HVLREG_ERRORS_H3     = HVL_Register(0x012d, HVL_DType.B2 , "")      # R
HVLREG_DEV_STATUS_H4 = HVL_Register(0x01c1, HVL_DType.B1 , "")      # R
# fmt: on

# ------------------------------------------------------------------------------
#   XylemHydrovarHVL
# ------------------------------------------------------------------------------


class XylemHydrovarHVL(SerialDevice):
    class State:
        """Container for the process and measurement variables."""

        pump_is_on = False
        actual_pressure = np.nan  # [bar]
        required_pressure = np.nan  # [bar]

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

    # --------------------------------------------------------------------------
    #   ID_validation_query
    # --------------------------------------------------------------------------

    def ID_validation_query(self) -> Tuple[bool, Union[int, None]]:
        # We're using a query on the Modbus slave address (P1205) as ID
        # validation
        success, data_val = self.RTU_read(HVLREG_ADDRESS)
        return success, data_val

    # --------------------------------------------------------------------------
    #   RTU_read
    # --------------------------------------------------------------------------

    def RTU_read(self, register: HVL_Register) -> Tuple[bool, Union[int, None]]:
        """Send a 'read' RTU command over Modbus to the slave device.

        Args:

        Returns:

        """
        # Construct 'read' command
        # fmt: off
        byte_cmd = bytearray(8)
        byte_cmd[0] = self.modbus_slave_address
        byte_cmd[1] = HVL_FuncCode.READ
        byte_cmd[2] = (register.address & 0xff00) >> 8  # address HI
        byte_cmd[3] = register.address & 0x00ff         # address LO
        byte_cmd[4] = 0x00                              # no. of points HI
        byte_cmd[5] = 0x01                              # no. of points LO
        # fmt: on
        byte_cmd[6:] = crc16(byte_cmd[:6])

        # Send command and read reply
        success, reply = self.query(byte_cmd, returns_ascii=False)

        # Parse the returned data value
        if success and isinstance(reply, bytes):
            data_val = (reply[3] << 8) + reply[4]

            if register.datum_type == HVL_DType.S08:
                data_val = data_val - 1 << 8
            elif register.datum_type == HVL_DType.S16:
                data_val = data_val - 1 << 16
        else:
            data_val = None

        return success, data_val

    # --------------------------------------------------------------------------
    #   RTU_write
    # --------------------------------------------------------------------------

    def RTU_write(
        self, register: HVL_Register, value: int
    ) -> Tuple[bool, Union[int, None]]:
        """Send a 'write' RTU command over Modbus to the slave device.

        Args:

        Returns:

        """
        # Construct 'write' command
        # fmt: off
        byte_cmd = bytearray(8)
        byte_cmd[0] = self.modbus_slave_address
        byte_cmd[1] = HVL_FuncCode.WRITE
        byte_cmd[2] = (register.address & 0xFF00) >> 8  # address HI
        byte_cmd[3] = register.address & 0x00FF         # address LO

        if (register.datum_type == HVL_DType.U08) or (
            register.datum_type == HVL_DType.U16
        ):
            byte_cmd[4] = (value & 0xFF00) >> 8         # data HI
            byte_cmd[5] = value & 0x00FF                # data LO
        else:
            # Not implemented (yet)
            pft("WARNING: Datum type not implemented (yet)")
            return False, None

        byte_cmd[6:] = crc16(byte_cmd[:6])
        # fmt: on

        # Send command and read reply
        success, reply = self.query(byte_cmd, returns_ascii=False)

        # Parse the returned data value
        if success and isinstance(reply, bytes):
            data_val = (reply[4] << 8) + reply[5]

            if register.datum_type == HVL_DType.S08:
                data_val = data_val - 1 << 8
            elif register.datum_type == HVL_DType.S16:
                data_val = data_val - 1 << 16
        else:
            data_val = None

        return success, data_val

    # --------------------------------------------------------------------------
    #
    # --------------------------------------------------------------------------

    def start_pump(self) -> bool:
        success, data_val = self.RTU_write(HVLREG_STOP_START, 1)
        if data_val is not None:
            self.state.pump_is_on = bool(data_val)
            print(f"Pump turned {'ON' if self.state.pump_is_on else 'OFF'}")

        return success

    def stop_pump(self) -> bool:
        success, data_val = self.RTU_write(HVLREG_STOP_START, 0)
        if data_val is not None:
            self.state.pump_is_on = bool(data_val)
            print(f"Pump turned {'ON' if self.state.pump_is_on else 'OFF'}")

        return success

    def read_actual_pressure(self) -> bool:
        success, data_val = self.RTU_read(HVLREG_ACTUAL_VALUE)
        if data_val is not None:
            self.state.actual_pressure = float(data_val) / 100
            print(f"Actual pressure: {self.state.actual_pressure:.2f} bar")

        return success

    def set_required_pressure(self, P_bar: float) -> bool:
        # Limit pressure setpoint
        MAX_PRESSURE = 1  # [bar]
        P_bar = max(float(P_bar), 0)
        P_bar = min(float(P_bar), MAX_PRESSURE)

        success, data_val = self.RTU_write(HVLREG_REQ_VAL_1, int(P_bar * 100))
        if data_val is not None:
            self.state.required_pressure = float(data_val) / 100
            print(f"Required pressure: {self.state.required_pressure:.2f} bar")

        return success

    def read_required_pressure(self) -> bool:
        success, data_val = self.RTU_read(HVLREG_REQ_VAL_1)
        if data_val is not None:
            self.state.required_pressure = float(data_val) / 100
            print(f"Required pressure: {self.state.required_pressure:.2f} bar")

        return success
