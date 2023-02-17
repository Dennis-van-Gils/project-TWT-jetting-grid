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
    cod. 001085110 rev. B ed. 01/2018
(2) Hydrovar HVL 2.015 - 4.220 | Installation, Operation, and Maintenance Manual
    cod. 001085102 rev. A ed. 01/2016
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/python-dvg-devices"
__date__ = "17-02-2023"
__version__ = "1.0.0"
# pylint: disable=invalid-name

import sys
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
    return msg.strip()


# ------------------------------------------------------------------------------
#   Enumerations
# ------------------------------------------------------------------------------


class HVL_FuncCode(IntEnum):
    # Implemented:
    READ = 0x03  # Read the contents of a single register
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
        """Container for the process and measurement variables"""

        # fmt: off
        pump_is_on        = False
        actual_pressure   = np.nan  # [bar]
        required_pressure = np.nan  # [bar] P820
        start_value       = np.nan  # [pct] P04
        pump_is_enabled   = False   #       P24
        # fmt: on

    class ErrorStatus:
        """Container for the Error Status bits (H3)"""

        # fmt: off
        overcurrent       = False  # bit 00, error 11
        overload          = False  # bit 01, error 12
        overvoltage       = False  # bit 02, error 13
        phase_loss        = False  # bit 03, error 16
        inverter_overheat = False  # bit 04, error 14
        motor_overheat    = False  # bit 05, error 15
        lack_of_water     = False  # bit 06, error 21
        minimum_threshold = False  # bit 07, error 22
        act_val_sensor_1  = False  # bit 08, error 23
        act_val_sensor_2  = False  # bit 09, error 24
        setpoint_1_low_mA = False  # bit 10, error 25
        setpoint_2_low_mA = False  # bit 11, error 26
        # fmt: on

        def report(self):
            error_list = (
                self.overcurrent,
                self.overload,
                self.overvoltage,
                self.phase_loss,
                self.inverter_overheat,
                self.motor_overheat,
                self.lack_of_water,
                self.minimum_threshold,
                self.act_val_sensor_1,
                self.act_val_sensor_2,
                self.setpoint_1_low_mA,
                self.setpoint_2_low_mA,
            )

            if not np.any(error_list, where=True):
                print("No errors")
                return

            print("ERRORS DETECTED")
            print("---------------")
            if self.overcurrent:
                print("- #11: OVERCURRENT")
            if self.overload:
                print("- #12: OVERLOAD")
            if self.overvoltage:
                print("- #13: OVERVOLTAGE")
            if self.phase_loss:
                print("- #16: PHASE LOSS")
            if self.inverter_overheat:
                print("- #14: INVERTER OVERHEAT")
            if self.motor_overheat:
                print("- #15: MOTOR OVERHEAT")
            if self.lack_of_water:
                print("- #21: LACK OF WATER")
            if self.minimum_threshold:
                print("- #22: MINIMUM THRESHOLD")
            if self.act_val_sensor_1:
                print("- #23: ACT VAL SENSOR 1")
            if self.act_val_sensor_2:
                print("- #24: ACT VAL SENSOR 2")
            if self.setpoint_1_low_mA:
                print("- #25: SETPOINT 1 I<4 mA")
            if self.setpoint_2_low_mA:
                print("- #26: SETPOINT 2 I<4 mA")

    class DeviceStatus:
        """Container for the Extended Device Status bits (H4)"""

        # fmt: off
        device_is_preset                    = False  # bit 00
        device_is_ready_for_regulation      = False  # bit 01
        device_has_an_error                 = False  # bit 02
        device_has_a_warning                = False  # bit 03
        external_ON_OFF_terminal_enabled    = False  # bit 04
        device_is_enabled_with_start_button = False  # bit 05
        motor_is_running                    = False  # bit 06
        solo_run_ON_OFF                     = False  # bit 14
        inverter_STOP_START                 = False  # bit 15
        # fmt: on

        def report(self):
            w = ".<38"  # Width specifier
            print("DEVICE STATUS")
            print("-------------")
            # fmt: off
            print(
                f"{'- Device is preset':{w}s} {self.device_is_preset}"
            )
            print(
                f"{'- Device is ready for regulation':{w}s} "
                f"{self.device_is_ready_for_regulation}"
            )
            print(
                f"{'- Device has an error':{w}s} {self.device_has_an_error}"
            )
            print(
                f"{'- Device has a warning':{w}s} {self.device_has_a_warning}"
            )
            print(
                f"{'- External ON/OFF terminal enabled':{w}s} "
                f"{self.external_ON_OFF_terminal_enabled}"
            )
            print(
                f"{'- Device is enabled with start button':{w}s} "
                f"{self.device_is_enabled_with_start_button}"
            )
            print(
                f"{'- Motor is running':{w}s} {self.motor_is_running}"
            )
            print(
                f"{'- Solo-Run ON/OFF':{w}s} {self.solo_run_ON_OFF}"
            )
            print(
                f"{'- Inverter STOP/START':{w}s} {self.inverter_STOP_START}"
            )
            # fmt: on

    def __init__(
        self,
        name: str = "HVL",
        long_name: str = "Xylem Hydrovar HVL variable speed drive",
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
        self.error_status = self.ErrorStatus()
        self.device_status = self.DeviceStatus()

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
        if register.datum_type == HVL_DType.B2:
            byte_cmd[5] = 0x02                          # no. of points LO
        else:
            byte_cmd[5] = 0x01                          # no. of points LO
        # fmt: on
        byte_cmd[6:] = crc16(byte_cmd[:6])

        # Send command and read reply
        success, reply = self.query(byte_cmd, returns_ascii=False)

        # Parse the returned data value
        if success and isinstance(reply, bytes):
            byte_count = reply[2]
            if byte_count == 2:
                data_val = (reply[3] << 8) + reply[4]
            elif byte_count == 4:  # HVL_DType.B2
                data_val = (
                    (reply[3] << 32)
                    + (reply[4] << 16)
                    + (reply[5] << 8)
                    + (reply[6])
                )
            else:
                pft("ERROR: Unsupported byte count")
                sys.exit()

            if register.datum_type == HVL_DType.S08:
                if data_val >= (1 << 7):
                    data_val = data_val - 1 << 8
            elif register.datum_type == HVL_DType.S16:
                if data_val >= (1 << 15):
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
            pft("ERROR: Datum type not implemented (yet)")
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
            val = bool(data_val)
            self.state.pump_is_on = val
            print(f"Pump turned {'ON' if val else 'OFF'}")

        return success

    def stop_pump(self) -> bool:
        success, data_val = self.RTU_write(HVLREG_STOP_START, 0)
        if data_val is not None:
            val = bool(data_val)
            self.state.pump_is_on = val
            print(f"Pump turned {'ON' if val else 'OFF'}")

        return success

    def enable_pump(self) -> bool:
        success, data_val = self.RTU_write(HVLREG_ENABLE_DEVICE, 1)
        if data_val is not None:
            val = bool(data_val)
            self.state.pump_is_enabled = val
            print(f"Pump is {'ENABLED' if val else 'DISABLED'}")

        return success

    def disable_pump(self) -> bool:
        success, data_val = self.RTU_write(HVLREG_ENABLE_DEVICE, 0)
        if data_val is not None:
            val = bool(data_val)
            self.state.pump_is_enabled = val
            print(f"Pump is {'ENABLED' if val else 'DISABLED'}")

        return success

    def read_actual_pressure(self) -> bool:
        success, data_val = self.RTU_read(HVLREG_ACTUAL_VALUE)
        if data_val is not None:
            val = float(data_val) / 100
            self.state.actual_pressure = val
            print(f"Actual pressure: {val:.2f} bar")

        return success

    def set_required_pressure(self, P_bar: float) -> bool:
        """P820: Sets the digital required value 1 in bar."""
        # Limit pressure setpoint
        MAX_PRESSURE = 1.5  # [bar]
        P_bar = max(float(P_bar), 0)
        P_bar = min(float(P_bar), MAX_PRESSURE)

        success, data_val = self.RTU_write(HVLREG_REQ_VAL_1, int(P_bar * 100))
        if data_val is not None:
            val = float(data_val) / 100
            self.state.required_pressure = val
            print(f"Set required pressure: {val:.2f} bar")

        return success

    def read_required_pressure(self) -> bool:
        """P820: Reads the digital required value 1 in bar."""
        success, data_val = self.RTU_read(HVLREG_REQ_VAL_1)
        if data_val is not None:
            val = float(data_val) / 100
            self.state.required_pressure = val
            print(f"Read required pressure: {val:.2f} bar")

        return success

    def set_start_value(self, pct: float) -> bool:
        """P04: This parameter defines, in percentage (0-100%) of the required
        value (P02 REQUIRED VAL.), the start value after pump stops. If P02
        REQUIRED VAL. is met and there is no more consumption, then the pump
        stops. The pump starts again when the pressure drops below P04 START
        VALUE. Value 100% makes this parameter not effective (100%=off)!
        """
        pct = max(pct, 0)
        pct = min(pct, 100)
        success, data_val = self.RTU_write(HVLREG_START_VALUE, int(pct))
        if data_val is not None:
            val = float(data_val)
            self.state.start_value = val
            print(f"Set start value: {val:.0f} %")

        return success

    def set_error_reset(self, flag: Union[int, bool]) -> bool:
        """P615: Selects automatic reset of errors"""
        success, data_val = self.RTU_write(HVLREG_ERROR_RESET, int(flag))
        if data_val is not None:
            val = int(data_val)
            print(f"Set error reset: {val}")

        return success

    def read_error_status(self) -> bool:
        success, data_val = self.RTU_read(HVLREG_ERRORS_H3)
        if data_val is not None:
            s = self.error_status  # Shorthand
            # fmt: off
            s.overcurrent       = bool(data_val & (1 << 0))
            s.overload          = bool(data_val & (1 << 1))
            s.overvoltage       = bool(data_val & (1 << 2))
            s.phase_loss        = bool(data_val & (1 << 3))
            s.inverter_overheat = bool(data_val & (1 << 4))
            s.motor_overheat    = bool(data_val & (1 << 5))
            s.lack_of_water     = bool(data_val & (1 << 6))
            s.minimum_threshold = bool(data_val & (1 << 7))
            s.act_val_sensor_1  = bool(data_val & (1 << 8))
            s.act_val_sensor_2  = bool(data_val & (1 << 9))
            s.setpoint_1_low_mA = bool(data_val & (1 << 10))
            s.setpoint_2_low_mA = bool(data_val & (1 << 11))
            # fmt: on
            s.report()

        return success

    def read_device_status(self) -> bool:
        success, data_val = self.RTU_read(HVLREG_DEV_STATUS_H4)
        if data_val is not None:
            s = self.device_status  # Shorthand
            # fmt: off
            s.device_is_preset                    = bool(data_val & (1 << 0))
            s.device_is_ready_for_regulation      = bool(data_val & (1 << 1))
            s.device_has_an_error                 = bool(data_val & (1 << 2))
            s.device_has_a_warning                = bool(data_val & (1 << 3))
            s.external_ON_OFF_terminal_enabled    = bool(data_val & (1 << 4))
            s.device_is_enabled_with_start_button = bool(data_val & (1 << 5))
            s.motor_is_running                    = bool(data_val & (1 << 6))
            s.solo_run_ON_OFF                     = bool(data_val & (1 << 14))
            s.inverter_STOP_START                 = bool(data_val & (1 << 15))
            # fmt: on
            s.report()

        return success
