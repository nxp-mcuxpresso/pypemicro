#!/usr/bin/env python
#
# Copyright (c) 2020 P&E Microcomputer Systems, Inc
# All rights reserved.
# Visit us at www.pemicro.com
#
# Copyright 2026 NXP
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
"""PEMicro DSC Python implementation by NXP.

This module contains DSC-specific functionality (JTAG IR/DR operations).
"""
import logging
from ctypes import CDLL, POINTER, byref, c_ubyte, c_ulong, c_ulonglong, c_void_p
from typing import Any, Optional

from .pemicro_base import PEMicroException, PyPemicroBase
from .pemicro_const_dsc import PEMicroDscSpecialFeatures

logger = logging.getLogger(__name__)


class PyPemicroDsc(PyPemicroBase):  # pylint: disable=duplicate-code
    """PEMicro DSC Debug probe Python class.

    This class extends PyPemicroBase with DSC-specific functionality
    including JTAG IR/DR shift register operations for DSC targets.
    """

    LIB_NAME_PREFIX = "unitdsc"

    @classmethod
    def open_library(cls, file_name: str) -> CDLL:
        """Open PEMicro DSC library with specified full path.

        Extends the base open_library with DSC-specific ctypes bindings.

        :param file_name: File Name of PEMicro dynamic library.
        :return: The loaded library CDLL object
        :raises PEMicroException: Cannot load the library
        """
        dll = super().open_library(file_name)

        # DSC library also supports 64-bit memory operations
        dll.read_64bit_value.argtypes = [c_ulong, c_ulong, c_void_p]
        dll.read_64bit_value.restype = c_ulonglong

        dll.write_64bit_value.argtypes = [c_ulong, c_ulong, c_ulonglong, c_void_p]

        # Override get_block with DSC-specific signature (POINTER(c_ubyte) instead of c_char_p)
        dll.get_block.argtypes = [
            c_ulong,
            c_ulong,
            c_ulong,
            c_ulong,
            POINTER(c_ubyte),
            c_void_p,
        ]

        logger.debug(f"DSC-specific library bindings applied: {file_name}")

        return dll

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
        logger.debug("PyPemicroDsc initialized")

    @property
    def connected_to_debug_cable(self) -> bool:
        """Returns if the connection to the debug cable is established."""
        return self._opened

    def connect_to_debug_cable(
        self, debug_hardware_name_ip_or_serialnum: Optional[str] = None
    ) -> None:
        """Connect to the debug cable.

        This is an alias for open() to maintain compatibility with the DSC workflow.

        :param debug_hardware_name_ip_or_serialnum: Hardware identifier
        :raises PEMicroException: If connection fails
        """
        self.open(debug_hardware_name_ip_or_serialnum or "")

    def jtag_init(self) -> None:
        """Initialize the JTAG TAP controller.

        Resets the JTAG TAP state machine and selects the CHIP_TAP.

        :raises PEMicroException: If the JTAG init operation fails.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        if not self._opened:
            raise PEMicroException("Not connected to debug cable")

        self._log_debug("JTAG TAP init")
        self.lib.pe_special_features(
            PEMicroDscSpecialFeatures.PE_DSC_JTAG_INIT, True, 0, 0, 0, 0, 0
        )

    def jtag_idle(self, num_bits: int = 1) -> None:
        """Perform JTAG idle cycles.

        :param num_bits: Number of idle cycles to perform
        :raises PEMicroException: If the operation fails.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        if not self._opened:
            raise PEMicroException("Not connected to debug cable")

        self.lib.pe_special_features(
            PEMicroDscSpecialFeatures.PE_DSC_JTAG_IDLE, True, num_bits, 0, 0, 0, 0
        )

    def write_ir(self, instruction: int, instruction_length: int) -> int:
        """Write to JTAG Instruction Register.

        :param instruction: Instruction value to write to IR.
        :param instruction_length: Bit length of the instruction.
        :return: Value shifted out during the IR write.
        :raises PEMicroException: If the IR write operation fails.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        if not self._opened:
            raise PEMicroException("Not connected to debug cable")

        self._log_debug(f"IR write: 0x{instruction:02X}, length={instruction_length}")
        ret_val = c_ulong()
        self.lib.pe_special_features(
            PEMicroDscSpecialFeatures.PE_DSC_WRITE_IR,
            True,
            instruction,
            instruction_length,
            0,
            byref(ret_val),
            0,
        )
        return ret_val.value

    def write_dr(self, bit_length: int, buffer: bytearray) -> bytearray:
        """Write to and read from JTAG Data Register.

        :param bit_length: Number of bits to shift through DR.
        :param buffer: Data buffer to write to DR.
        :return: Data read from DR during the shift operation.
        :raises PEMicroException: If the DR operation fails.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        if not self._opened:
            raise PEMicroException("Not connected to debug cable")

        self._log_debug(f"DR write: {bit_length} bits, data={buffer.hex()}")
        result = self.lib.pe_special_features(
            PEMicroDscSpecialFeatures.PE_DSC_WRITE_DR,
            True,
            bit_length,
            0,
            0,
            (c_ubyte * len(buffer)).from_buffer(buffer),
            0,
        )
        if not result:
            return bytearray()
        result_ba = bytearray(buffer)
        self._log_debug(f"DR read:  {bit_length} bits, data={result_ba.hex()}")
        return result_ba

    def target_set_reset_pin(self, reset_pin_value: bool) -> None:
        """Control the reset pin at the target.

        :param reset_pin_value: True to release reset, False to assert reset.
        :raises PEMicroException: If the operation fails.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        self._log_debug(f"Reset pin: {'RELEASE' if reset_pin_value else 'ASSERT'}")
        self.lib.set_reset_pin_state(1 if reset_pin_value else 0)
