#!/usr/bin/env python
#
# Copyright (c) 2020 P&E Microcomputer Systems, Inc
# All rights reserved.
# Visit us at www.pemicro.com
#
# Copyright 2020-2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# o Redistributions of source code must retain the above copyright notice, this list
#   of conditions and the following disclaimer.
#
# o Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or
#   other materials provided with the distribution.
#
# o Neither the names of the copyright holders nor the names of the
#   contributors may be used to endorse or promote products derived from this
#   software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# This file has been modified by NXP to update it to be usable as a separate package
# PEMicro company has been notified and they are agree.
"""PEMicro ARM Python implementation by NXP.

The basics of the code is coming from original PEMicro version.
This module contains ARM-specific functionality (SWD/JTAG CoreSight).
"""
import logging
from ctypes import byref, c_char_p, c_ulong
from typing import Any, List, Optional

from .pemicro_base import PEMicroException, PyPemicroBase
from .pemicro_const import (
    PEMicroArmRegisters,
    PEMicroInterfaces,
    PEMicroSpecialFeatures,
    PEMicroSpecialFeaturesSwdStatus,
)


class PEMicroTransferException(PEMicroException):
    """PEMicro Transfer exception."""


logger = logging.getLogger(__name__)


class PyPemicro(PyPemicroBase):
    """PEMicro ARM Debug probe Python class.

    This class extends PyPemicroBase with ARM-specific functionality
    including SWD/JTAG CoreSight access port and debug port operations.
    """

    LIB_NAME_PREFIX = "unitacmp"

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        dll_path: Optional[str] = None,
        log_info: Any = None,
        log_war: Any = None,
        log_err: Any = None,
        log_debug: Any = None,
    ) -> None:
        """Class initialization.

        :param dll_path: The way to force the own path for PEMicro DLLs.
        :param log_info: Log function - info level.
        :param log_war: Log function - warning level.
        :param log_err: Log function - error level.
        :param log_debug: Log function - debug level.
        """
        super().__init__(dll_path, log_info, log_war, log_err, log_debug)
        self.interface = PEMicroInterfaces.SWD

    def _special_features(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        featurenum: int,
        fset: bool = True,
        par1: int = 0,
        par2: int = 0,
        par3: int = 0,
        ref1: Any = None,
        ref2: Any = None,
    ) -> None:
        """Help private function to simplify calling special PEMicro features.

        :param featurenum: Feature index/number.
        :param fset: Set feature.
        :param par1: First parameter.
        :param par2: Second parameter.
        :param par3: Third parameter.
        :param ref1: Reference to first return value.
        :param ref2: Reference to second return value.
        :raises PEMicroException: Various kind of problems.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        if not isinstance(featurenum, PEMicroSpecialFeatures):
            raise PEMicroException("Invalid argument to do special feature")

        if self.lib.pe_special_features(featurenum, fset, par1, par2, par3, ref1, ref2) is False:
            raise PEMicroException("The special feature command hasn't accepted")

    def close(self) -> None:
        """Close the connection and also it close the opened DLL library."""
        if not self._opened:
            return

        # Flush queued data before closing (ARM-specific)
        self._special_features(PEMicroSpecialFeatures.PE_ARM_FLUSH_ANY_QUEUED_DATA)

        super().close()

    def get_mcu_register(self, reg: PEMicroArmRegisters) -> int:
        """Method gets the current value of core register.

        :param reg: The index of register to get
        :return: The value of read register
        :raises PEMicroException: Various kind of exceptions.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        if not isinstance(reg, PEMicroArmRegisters):
            raise PEMicroException("Invalid register index")

        ret_val = c_ulong()

        if self.lib.get_mcu_register(0, reg, ret_val) is False:
            raise PEMicroException(f"Getting of MCU register{str(reg)} fails")

        return ret_val.value

    def set_mcu_register(self, reg: PEMicroArmRegisters, value: int) -> None:
        """Method sets the new value of core register.

        :param reg: The index of register to get
        :param value: A new value that should be use for selected register
        :raises PEMicroException: Various kind of exceptions.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        if not isinstance(reg, PEMicroArmRegisters):
            raise PEMicroException("Invalid register index")

        if self.lib.set_mcu_register(0, reg, value) is False:
            raise PEMicroException(f"Setting of new MCU register{str(reg)} value{value:X08} fails")

    def flush_any_queued_data(self) -> None:
        """Function flush any possible queued data in DLL->Probe->Target.

        :raises PEMicroException: Check to active connection.
        """
        if not self._opened:
            raise PEMicroException("The connection is not active")

        self._log_debug("All queued data has been flushed")
        self._special_features(PEMicroSpecialFeatures.PE_ARM_FLUSH_ANY_QUEUED_DATA)

    def set_device_name(self, device_name: str = "Cortex-M4") -> None:
        """Set the name of device.

        :param device_name:
        :raises PEMicroException: Check to opened connection.
        """
        if self._opened:
            raise PEMicroException("The connection is already opened, can't change the device name")

        self._log_debug(f"The device name is set to {device_name}")

        self._special_features(
            PEMicroSpecialFeatures.PE_GENERIC_SELECT_DEVICE,
            ref1=device_name.encode("utf-8"),
        )

    def get_device_list(self, search_string: Optional[str] = None) -> List:
        """Get the device list.

        :param search_string: The participial string to filter results.
        :raises PEMicroException: Check to opened connection.
        :return: List of all devices
        """
        max_buff_len = 1000000
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        ret_val = c_char_p(bytes(max_buff_len))

        try:
            self._special_features(
                PEMicroSpecialFeatures.PE_GENERIC_GET_DEVICE_LIST,
                par1=max_buff_len - 1,
                ref1=ret_val,
                ref2=None if search_string is None else search_string.encode("utf-8"),
            )
        except PEMicroException as exc:
            raise PEMicroException(
                f"It is impossible to retrieve PEMicro device list:{str(exc)}."
            ) from exc

        value = ret_val.value
        # pylint: disable=no-member,using-constant-test
        return value.decode().split(",") if value else []

    def connect(
        self,
        interface: PEMicroInterfaces = PEMicroInterfaces.SWD,
        shift_speed: int = 1000000,
    ) -> None:
        """Connect to target.

        :param interface: Select the communication interface.
        :param shift_speed: Set the communication speed.
        :raises PEMicroException: Various reasons for interrupt connect operation.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        if not self._opened:
            raise PEMicroException("The connection is not opened, can't connect to target")
        self._log_debug(f"Selecting the communication interface to {str(interface)}")
        self.interface = interface
        if self.interface is PEMicroInterfaces.SWD:
            self._special_features(
                PEMicroSpecialFeatures.PE_ARM_SET_COMMUNICATIONS_MODE,
                par1=PEMicroSpecialFeatures.PE_ARM_SET_DEBUG_COMM_SWD,
            )
        else:
            self._special_features(
                PEMicroSpecialFeatures.PE_ARM_SET_COMMUNICATIONS_MODE,
                par1=PEMicroSpecialFeatures.PE_ARM_SET_DEBUG_COMM_JTAG,
            )
        # Set 1Mhz as a default or given value by parameter shift_speed for communication speed
        self.lib.set_debug_shift_frequency(shift_speed)
        # Communicate to the target, power up debug module, check  (powering it up).
        # Looks for arm IDCODE to verify connection.
        try:
            self._special_features(PEMicroSpecialFeatures.PE_ARM_ENABLE_DEBUG_MODULE)
        except PEMicroException as exc:
            raise PEMicroException(f"Failed to connect to target: {str(exc)}") from exc

        self._log_info(
            f"Connected to target over "
            f"{PEMicroInterfaces.get_str(interface)} with clock {shift_speed}Hz"
        )

    def __check_swd_error(self) -> None:
        """The function checks and solve errors on SWD bus.

        :raises PEMicroTransferException: Error in SWD transfer
        :raises PEMicroException: The check for loaded PEMicro DLL
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        swd_status = self.last_swd_status()

        if swd_status is not int(PEMicroSpecialFeaturesSwdStatus.PE_ARM_SWD_STATUS_ACK):
            if swd_status is not int(PEMicroSpecialFeaturesSwdStatus.PE_ARM_SWD_STATUS_WAIT):
                # Verify that the connection to the P&E hardware interface is good.
                probe_error = self.lib.check_critical_error()

                if probe_error & 0x08:
                    # Connect and initialize the P&E hardware interface.
                    self.lib.reset_hardware_interface()

                try:
                    self.reset_target()
                except Exception:  # pylint: disable=broad-except
                    self._log_debug(
                        "Cannot reset target properly, resume normal state of reset pin."
                    )
                    self.control_reset_line(assert_reset=False)

                self._log_warning(
                    f"SWD Status failed during IO operation. status: 0x{swd_status:02X},"
                    f"the communication has been resumed by reset target sequence."
                )

            raise PEMicroTransferException(
                f"SWD Status failed during IO operation. status: 0x{swd_status:02X}"
            )

    def write_ap_register(self, apselect: int, addr: int, value: int, now: bool = False) -> None:
        """Write Access port register.

        Function writes the access port coresight register.
        :param apselect: Selection of access port
        :param addr: Register address
        :param value: Value of register to write
        :param now: Delayed or immediate write
        :raises PEMicroException: Writing error
        """
        if not self._opened:
            raise PEMicroException("There is NO opened connection with target")

        self._log_debug(
            f"Writing into AP register: Addr: 0x{addr:08X}, "
            f"Value:{value}, 0x{value:08X}, now?{now}"
        )

        self._special_features(
            PEMicroSpecialFeatures.PE_ARM_WRITE_AP_REGISTER,
            fset=now,
            par1=apselect,
            par2=addr,
            par3=value,
        )

        # Check the status of SWD
        self.__check_swd_error()

    # pylint: disable=unused-argument
    def read_ap_register(
        self, apselect: int, addr: int, now: bool = True, requires_delay: bool = False
    ) -> int:
        """Read Access port register.

        Function reads the access port coresight register.
        :param apselect: Selection of access port
        :param addr: Register address
        :param now: Delayed or immediate read
        :param requires_delay: Obsolete parameter - do not use it
        :return: Value of read register
        :raises PEMicroException: Reading error
        """
        if not self._opened:
            raise PEMicroException("There is no opened connection with target")
        ret_val = c_ulong()
        self._special_features(
            PEMicroSpecialFeatures.PE_ARM_READ_AP_REGISTER,
            fset=True,
            par1=apselect,
            par2=addr,
            ref1=byref(ret_val),
        )

        self._log_debug(
            f"Read AP register: Addr: 0x{addr:08X}, "
            f"Value:{ret_val.value}, 0x{ret_val.value:08X}"
        )
        # Check the status of SWD
        self.__check_swd_error()

        return ret_val.value

    def write_dp_register(self, addr: int, value: int, now: bool = False) -> None:
        """Write Debug port register.

        Function writes the debug port coresight register.
        :param addr: Register address
        :param now: Delayed or immediate write
        :param value: Value of register to write
        :raises PEMicroException: Writing error
        """
        if not self._opened:
            raise PEMicroException("There is no opened connection with target")

        self._log_debug(
            f"Writing into DP register: Addr: 0x{addr:08X}, "
            f"Value:{value}, 0x{value:08X}, now?:{now}"
        )

        self._special_features(
            PEMicroSpecialFeatures.PE_ARM_WRITE_DP_REGISTER,
            fset=now,
            par1=addr,
            par2=value,
        )

        # Check the status of SWD
        self.__check_swd_error()

    def read_dp_register(self, addr: int, now: bool = True, requires_delay: bool = False) -> int:
        """Read Debug port register.

        Function reads the debug port coresight register.
        :param addr: Register address
        :param now: Delayed or immediate read
        :param requires_delay: Obsolete parameter - do not use it
        :return: Value of read register
        :raises PEMicroException: Reading error
        """
        if not self._opened:
            raise PEMicroException("There is no opened connection with target")
        ret_val = c_ulong()
        self._special_features(
            PEMicroSpecialFeatures.PE_ARM_READ_DP_REGISTER,
            fset=True,
            par1=addr,
            ref1=byref(ret_val),
        )

        self._log_debug(
            f"Read DP register: Addr: 0x{addr:08X}, "
            f"Value:{ret_val.value}, 0x{ret_val.value:08X}"
        )

        # Check the status of SWD
        self.__check_swd_error()

        return ret_val.value

    def last_swd_status(self) -> int:
        """Get last SWD protocol status.

        The functions returns the latest SWD status.
        :return: The last SWD status
        """
        ret_val = c_ulong()
        self._special_features(
            PEMicroSpecialFeatures.PE_ARM_GET_LAST_SWD_STATUS, ref1=byref(ret_val)
        )
        self._log_debug("Got last SWD status:{val}, 0x{val:08X}".format(val=ret_val.value))
        return ret_val.value
