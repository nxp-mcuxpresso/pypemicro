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
"""PEMicro Base Python implementation by NXP.

This module contains the common base class for PyPemicro (ARM) and PyPemicroDsc (DSC).
"""
import logging
import os.path
import platform
import sys
from ctypes import CDLL, byref, c_bool, c_byte, c_char_p, c_ulong, c_ushort, c_void_p
from typing import Any, Dict, List, Optional

from .pemicro_const import (
    PEMicroMemoryAccessResults,
    PEMicroMemoryAccessSize,
    PEMicroPortType,
    PEMicroSpecialFeatures,
)


class PEMicroException(Exception):
    """The base PEMicro implementation exception."""


logger = logging.getLogger(__name__)


class PyPemicroBase:  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    """PEMicro Debug probe Python base class.

    This class provides common functionality shared between ARM and DSC probes.
    Subclasses should set LIB_NAME_PREFIX to select the correct native library.
    """

    LIB_NAME_PREFIX = ""
    """Override in subclass: 'unitacmp' for ARM, 'unitdsc' for DSC."""

    @staticmethod
    def get_user_friendly_os_name() -> str:
        """Get user friendly os name.

        :return: User friendly OS name (Windows, Linux, MacOS).
        """
        systems = {
            "Windows": "Windows",
            "Linux": "Linux",
            "Linux2": "Linux",
            "Darwin": "MacOS",
            "FreeBSD": "FreeBSD",
            "OpenBSD": "OpenBSD",
            "NetBSD": "NetBSD",
        }
        return systems[platform.system()]

    @classmethod
    def get_library_name(cls) -> str:
        """Get library name.

        Just help function to get right library name depending on used OS.
        :return: Name of library to use on current running system.
        """
        prefix = cls.LIB_NAME_PREFIX
        extensions = {
            "Windows": {"32bit": f"{prefix}-32.dll", "64bit": f"{prefix}-64.dll"},
            "Linux": {"32bit": f"{prefix}-64.so", "64bit": f"{prefix}-64.so"},
            "Darwin": {"32bit": f"{prefix}-64.dylib", "64bit": f"{prefix}-64.dylib"},
            "FreeBSD": {"32bit": f"{prefix}-64.so", "64bit": f"{prefix}-64.so"},
            "OpenSD": {"32bit": f"{prefix}-64.so", "64bit": f"{prefix}-64.so"},
            "NetBSD": {"32bit": f"{prefix}-64.so", "64bit": f"{prefix}-64.so"},
        }

        pointer_size = "64bit" if sys.maxsize > 2**32 else "32bit"
        system_name = platform.system()
        if system_name not in extensions:
            raise PEMicroException(
                f"Unable to determinate running operation system ({system_name})"
            )

        return extensions[system_name][pointer_size]

    @classmethod
    def _load_pemicro_lib_info(cls, dll_path: str, lib_name: str) -> Dict:
        """Get the PEMicro library info.

        Help function to try load and fill up information
        about the Pemicro DLL on specified path.
        :param dll_path: path to look for the library.
        :param lib_name: name of the library.
        :return: Fill up information about library on specified path
        :raises PEMicroException: Cannot load the library
        """
        try:
            lib_info = {}
            lib_info["path"] = dll_path
            lib_info["name"] = lib_name
            dll = CDLL(os.path.join(dll_path, lib_name))

            # char * version(void);
            dll.version.restype = c_char_p
            # unsigned short get_dll_version(void);
            dll.get_dll_version.restype = c_ushort

            lib_info["version"] = dll.version()
            lib_info["version_num"] = dll.get_dll_version()
            del dll
        except (FileNotFoundError, OSError) as exc:
            raise PEMicroException(
                f"Cannot load the PEMICRO library({lib_name})"
                + f"on this path:{dll_path}. Error({str(exc)})"
            ) from exc
        return lib_info

    @classmethod
    def get_pemicro_lib_list(
        cls, dll_path: Optional[str] = None, search_generic: bool = True
    ) -> List:
        """Gets the description list of PEMicro DLLs.

        :param dll_path: User way to add specific a DLL path.
        :param search_generic: If it's True, the engine search also in general places in system.
        :return: The List of search results.
        :raises PEMicroException: Various kind of issues
        """
        # Get the name of PEMicro dynamic library
        lib_name = cls.get_library_name()

        library_dlls = []
        if dll_path is not None:
            try:
                library_dlls.append(cls._load_pemicro_lib_info(dll_path, lib_name))
            except PEMicroException:
                pass

        if search_generic:
            # Look in System Folders
            try:
                library_dlls.append(cls._load_pemicro_lib_info("", lib_name))
            except PEMicroException:
                pass
            # Look in the folder with .py file
            try:
                library_dlls.append(cls._load_pemicro_lib_info(os.path.dirname(__file__), lib_name))
            except PEMicroException:
                pass
            # Look in a local library storage snapshot
            try:
                os_utility_path = os.path.join("libs", PyPemicroBase.get_user_friendly_os_name())
                library_dlls.append(
                    cls._load_pemicro_lib_info(
                        os.path.join(os.path.dirname(__file__), os_utility_path),
                        lib_name,
                    )
                )
            except PEMicroException:
                pass

        if len(library_dlls) == 0:
            logger.debug("There is no PEMICRO library.")

        return library_dlls

    @classmethod
    def open_library(cls, file_name: str) -> CDLL:  # pylint: disable=too-many-statements
        """Open PEMicro library with specified full path.

        :param file_name: File Name of PEMicro dynamic library.
        :return: The loaded library CDLL object
        :raises PEMicroException: Cannot load the library
        """
        if file_name is None:
            raise PEMicroException("The library file name MUST be specified.")

        try:
            dll = CDLL(file_name)
        except (FileNotFoundError, OSError) as exc:
            raise PEMicroException(
                f"Cannot load the PEMICRO library({file_name}). " + f"Error({str(exc)})"
            ) from exc

        if dll is None:
            raise PEMicroException("The PEMicro library load failed.")

        # === Common function signatures shared by ARM and DSC libraries ===

        # bool pe_special_features(unsigned long featurenum,
        #                         bool set_feature,
        #                         unsigned long paramvalue1,
        #                         unsigned long paramvalue2,
        #                         unsigned long paramvalue3,
        #                         void *paramreference1,
        #                         void *paramreference2);
        dll.pe_special_features.argtypes = [
            c_ulong,
            c_bool,
            c_ulong,
            c_ulong,
            c_ulong,
            c_void_p,
            c_void_p,
        ]
        dll.pe_special_features.restype = c_bool

        # bool open_port(unsigned int PortType, unsigned int PortNum);
        dll.open_port.argtypes = [c_ulong, c_ulong]
        dll.open_port.restype = c_bool

        dll.open_port_by_identifier.argtypes = [c_char_p]
        dll.open_port_by_identifier.restype = c_bool

        # bool reenumerate_all_port_types(void);
        dll.reenumerate_all_port_types.restype = c_bool

        # unsigned int get_enumerated_number_of_ports(unsigned int PortType);
        dll.get_enumerated_number_of_ports.argtypes = [c_ulong]
        dll.get_enumerated_number_of_ports.restype = c_ulong

        # char * get_port_descriptor(unsigned int PortType, unsigned int PortNum);
        dll.get_port_descriptor.argtypes = [c_ulong, c_ulong]
        dll.get_port_descriptor.restype = c_char_p

        # char * get_port_descriptor_short(unsigned int PortType, unsigned int PortNum);
        dll.get_port_descriptor_short.argtypes = [c_ulong, c_ulong]
        dll.get_port_descriptor_short.restype = c_char_p

        # void reset_hardware_interface(void);
        #  No parameters and return value

        # unsigned char check_critical_error(void);
        dll.check_critical_error.restype = c_byte

        # char * version(void);
        dll.version.restype = c_char_p

        # unsigned short get_dll_version(void);
        dll.get_dll_version.restype = c_ushort

        # void set_debug_shift_frequency (signed long shift_speed_in_hz);
        dll.set_debug_shift_frequency.argtypes = [c_ulong]

        # void set_reset_delay_in_ms(unsigned int delaylength);
        dll.set_reset_delay_in_ms.argtypes = [c_ulong]

        # bool target_reset(void);
        dll.target_reset.restype = c_bool

        # bool target_check_if_halted(void)
        dll.target_check_if_halted.restype = c_bool

        # bool target_halt(void);
        dll.target_halt.restype = c_bool

        # bool target_resume(void);
        dll.target_resume.restype = c_bool

        # bool target_step(void)
        dll.target_step.restype = c_bool

        # void set_reset_pin_state(unsigned char state)
        dll.set_reset_pin_state.argtypes = [c_byte]

        # void open_debug_file(char *filename)
        dll.open_debug_file.argtypes = [c_char_p]

        # unsigned long read_32bit_value(unsigned long memory_access_tag, unsigned long address,
        #                                mem_result *optional_mem_result)
        dll.read_32bit_value.argtypes = [c_ulong, c_ulong, c_void_p]
        dll.read_32bit_value.restype = c_ulong

        # void write_32bit_value(...)
        dll.write_32bit_value.argtypes = [c_ulong, c_ulong, c_ulong, c_void_p]

        # unsigned short read_16bit_value(...)
        dll.read_16bit_value.argtypes = [c_ulong, c_ulong, c_void_p]
        dll.read_16bit_value.restype = c_ushort

        # void write_16bit_value(...)
        dll.write_16bit_value.argtypes = [c_ulong, c_ulong, c_ulong, c_void_p]

        # unsigned char read_8bit_value(...)
        dll.read_8bit_value.argtypes = [c_ulong, c_ulong, c_void_p]
        dll.read_8bit_value.restype = c_byte

        # void write_8bit_value(...)
        dll.write_8bit_value.argtypes = [c_ulong, c_ulong, c_ulong, c_void_p]

        # bool get_block(...)
        dll.get_block.argtypes = [
            c_ulong,
            c_ulong,
            c_ulong,
            c_ulong,
            c_char_p,
            c_char_p,
        ]
        dll.get_block.restype = c_bool

        # bool put_block(...)
        dll.put_block.argtypes = [
            c_ulong,
            c_ulong,
            c_ulong,
            c_ulong,
            c_char_p,
            c_char_p,
        ]
        dll.put_block.restype = c_bool

        # bool load_bin_file(char *filename, unsigned int start_address)
        dll.load_bin_file.argtypes = [c_char_p, c_ulong]
        dll.load_bin_file.restype = c_bool

        # bool load_srec_file(char *filename, unsigned int start_address)
        dll.load_srec_file.argtypes = [c_char_p, c_ulong]
        dll.load_srec_file.restype = c_bool

        # bool get_mcu_register(...)
        dll.get_mcu_register.argtypes = [c_ulong, c_ulong, c_void_p]
        dll.get_mcu_register.restype = c_bool

        # bool set_mcu_register(...)
        dll.set_mcu_register.argtypes = [c_ulong, c_ulong, c_ulong]
        dll.set_mcu_register.restype = c_bool

        if (
            dll.pe_special_features(
                PEMicroSpecialFeatures.PE_SET_DEFAULT_APPLICATION_FILES_DIRECTORY,
                True,
                0,
                0,
                0,
                c_char_p(os.path.dirname(os.path.abspath(file_name).encode("utf-8"))),
                None,
            )
            is False
        ):
            raise PEMicroException("The special feature command hasn't been accepted")

        logger.debug(f"Opened PEMicro library: {file_name}, {dll.version()}.")

        return dll

    @classmethod
    def get_lib_filename(cls, lib_record: Dict) -> str:
        """Get the filename from the library dictionary record.

        :param lib_record: Input dictionary record.
        :return: File name path in string.
        """
        return os.path.join(lib_record["path"], lib_record["name"])

    @classmethod
    def get_newest_lib_filename(cls, lib_list: List) -> str:
        """Gets the latest version of PEMicro library from list.

        :param lib_list: List of PEMicro libraries in system.
        :return: The absolute path to PEMicro library.
        :raises PEMicroException: Various kind of issues
        """
        if lib_list is None:
            raise PEMicroException("The input list must exists")

        if len(lib_list) == 0:
            raise PEMicroException("Unable to find any usable library in the system!")

        ver_ix = 0
        for count, item in enumerate(lib_list):
            if item["version_num"] > lib_list[ver_ix]["version_num"]:
                ver_ix = count

        return cls.get_lib_filename(lib_list[ver_ix])

    @classmethod
    def get_pemicro_lib(cls, dll_path: Optional[str] = None, get_newest: bool = True) -> CDLL:
        """Gets the best possible PEMicro DLL.

        :param dll_path: User way to force the DLL path.
        :param get_newest: If it's true the latest version of DLL is used.
        :return: The PEMicro CDLL Python object.
        :raises PEMicroException: Various kind of issues
        """
        try:
            libs_list = cls.get_pemicro_lib_list(dll_path=dll_path)
            if len(libs_list) == 0:
                raise PEMicroException("There is any suitable library for this OS.")
            if get_newest:
                filename = cls.get_newest_lib_filename(libs_list)
            else:
                filename = cls.get_lib_filename(libs_list[0])
        except PEMicroException as exc:
            raise PEMicroException(str(exc)) from exc

        return cls.open_library(filename)

    @classmethod
    def list_ports(cls) -> List:
        """Get list of all connected PEMicro probes.

        :return: List of all connected probes to system.
        :raises PEMicroException: The library is not loaded.
        """
        try:
            lib = cls.get_pemicro_lib()
        except PEMicroException as exc:
            raise PEMicroException(str(exc)) from exc

        num_ports = lib.get_enumerated_number_of_ports(PEMicroPortType.AUTODETECT)
        ports = []
        for i in range(1, num_ports + 1):
            ports.append(
                {
                    "id": lib.get_port_descriptor_short(PEMicroPortType.AUTODETECT, i).decode(
                        "utf-8"
                    ),
                    "description": lib.get_port_descriptor(PEMicroPortType.AUTODETECT, i).decode(
                        "utf-8"
                    ),
                }
            )
        del lib
        return ports

    @staticmethod
    def print_ports(ports: List) -> None:
        """Print the all probes from list that is using list_port() function.

        :param ports: Input list of probes to print.
        """
        if ports is None or len(ports) == 0:
            logger.info("No hardware detected locally.")
        i = 0
        for port in ports:
            logger.info(f"{i:>2}: {port['id']} => {port['description']}")
            i += 1

    @classmethod
    def list_ports_name(cls) -> None:
        """List to logger (info level) the all connected PEMicro probe names.

        :raises PEMicroException: Usually that the port is not opened.
        """
        try:
            lib = cls.get_pemicro_lib()
        except PEMicroException as exc:
            raise PEMicroException(str(exc)) from exc

        num_ports = lib.get_enumerated_number_of_ports(PEMicroPortType.AUTODETECT)
        if num_ports == 0:
            logger.info("No hardware detected locally.")
        for i in range(1, num_ports + 1):
            logger.info(
                lib.get_port_descriptor_short(PEMicroPortType.AUTODETECT, i).decode("utf-8")
            )

        del lib

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
        self._opened = False
        self.dll_path = dll_path
        self.lib: Optional[CDLL] = None
        self.lib = self.__class__.get_pemicro_lib(dll_path)

        self.opened_debug_file = False

        # register logging objects
        self._log_info = log_info or logger.info
        self._log_warning = log_war or logger.warning
        self._log_error = log_err or logger.error
        self._log_debug = log_debug or logger.debug

        # Set as a default the path to this package
        self.set_application_files_directory(os.path.dirname(__file__))

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

        if (
            self.lib.pe_special_features(  # pylint: disable=no-member
                featurenum, fset, par1, par2, par3, ref1, ref2
            )
            is False
        ):
            raise PEMicroException("The special feature command hasn't accepted")

    def set_application_files_directory(self, directory: str) -> None:
        """Set the application files directory.

        :param directory: Path to PEMicro application files
        :raises PEMicroException: Invalid directory.
        """
        if not isinstance(directory, str) or not os.path.exists(directory):
            raise PEMicroException("Invalid input directory.")

        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        if (
            self.lib.pe_special_features(
                PEMicroSpecialFeatures.PE_SET_DEFAULT_APPLICATION_FILES_DIRECTORY,
                True,
                0,
                0,
                0,
                c_char_p((directory).encode("utf-8")),
                None,
            )
            is False
        ):
            raise PEMicroException("The special feature command hasn't accepted")

    def reenumerate_all_port_types(self) -> None:
        """Reenumerate of usable interface for PEMicro.

        This call rescans the USB and Ethernet ports to enumerate
        all the P&E hardware interfaces.
        :raises PEMicroException: Various kind of problems.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        if self.lib.reenumerate_all_port_types() is not True:
            raise PEMicroException("Re-enumeration of PE interfaces failed.")

    def open(self, debug_hardware_name_ip_or_serialnum: str) -> None:
        """This function opens the connection to PEMicro debug probe.

        :param debug_hardware_name_ip_or_serialnum: Hardware identifier of PEMicro debug probe
        :raises PEMicroException: With any problem with probe itself
        """
        if self.lib is None:
            raise PEMicroException("The PEMicro library loader failed.")

        if self._opened:
            logger.warning("The PEMicro probe is already opened")
            return

        if debug_hardware_name_ip_or_serialnum is None:
            port_name = c_char_p("USB1".encode("utf-8"))
        else:
            port_name = c_char_p(debug_hardware_name_ip_or_serialnum.encode("utf-8"))

        if not self.lib.open_port_by_identifier(port_name):
            raise PEMicroException("Cannot connect to debug probe")

        self._opened = True

        # Connect and initialize the P&E hardware interface.
        self.lib.reset_hardware_interface()

        # Verify that the connection to the P&E hardware interface is good.
        probe_error = self.lib.check_critical_error()

        if probe_error:
            raise PEMicroException(
                f"Probe error has been detected during open operation. Error: 0x{probe_error:02X}"
            )

    @property
    def opened(self) -> bool:
        """Returns if the library is opened or not."""
        return self._opened

    def close(self) -> None:
        """Close the connection and also it close the opened DLL library."""
        if not self._opened:
            return

        if self.opened_debug_file:
            self.close_debug_file()

        if self.lib is not None:
            self.lib.close_port()

        self._opened = False

    def __del__(self) -> None:
        """Action for deleting the class instance."""
        self.close()
        if self.lib is not None:
            del self.lib
            self.lib = None

    def open_debug_file(self, filename: str = "log_pemicro_comm.txt") -> None:
        """Log the debug communication into file.

        :param filename: File name to be used to store the debug communication.
        :raises PEMicroException: Various kind of problems.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        self.lib.open_debug_file(filename.encode())
        self.opened_debug_file = True

    def close_debug_file(self) -> None:
        """Close the debug log file.

        :raises PEMicroException: Various kind of problems.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        self.lib.close_debug_file()
        self.opened_debug_file = False

    def power_on(self) -> None:
        """Power on target."""
        self._log_debug("Power on target")
        self._special_features(PEMicroSpecialFeatures.PE_PWR_TURN_POWER_ON)

    def power_off(self) -> None:
        """Power off target."""
        self._log_debug("Power off target")
        self._special_features(PEMicroSpecialFeatures.PE_PWR_TURN_POWER_OFF)

    def reset_target(self) -> None:
        """Reset target.

        :raises PEMicroException: Various kind of exceptions.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        self._log_debug("Reset target")
        if self.lib.target_reset() is not True:
            raise PEMicroException("Reset target sequence failed")

    def target_check_if_halted(self) -> bool:
        """Check to see if the CPU is halted in debug mode.

        :return: True if is halted, False Otherwise.
        :raises PEMicroException: Various kind of exceptions.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        return self.lib.target_check_if_halted()

    def target_step(self) -> None:
        """Do one assembly step.

        :raises PEMicroException: Various kind of exceptions.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        if self.lib.target_step() is False:
            raise PEMicroException("Target step failed")

    def halt_target(self) -> None:
        """Halt target.

        :raises PEMicroException: Various kind of exceptions.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        self._log_debug("Halt target")

        if self.lib.target_halt() is not True:
            raise PEMicroException("Halt target sequence failed")

    def resume_target(self) -> None:
        """Resume target.

        :raises PEMicroException: Various kind of exceptions.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        self._log_debug("Resume target")

        if self.lib.target_resume() is not True:
            raise PEMicroException("Resume target sequence failed")

    def set_reset_delay_in_ms(self, delay: int) -> None:
        """Set the Reset delay.

        :raises PEMicroException: Check to load library.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        self._log_debug(f"Reset target delay has been set to {delay}ms")
        self.lib.set_reset_delay_in_ms(delay)

    def set_debug_frequency(self, freq: int) -> None:
        """Set debug interface frequency.

        :raises PEMicroException: When any problems occurs
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        if not self._opened:
            raise PEMicroException("The communication interface is not opened")
        self._log_debug(f"The communication speed has been switched to {freq}Hz")

        self.lib.set_debug_shift_frequency(freq)

    def control_reset_line(self, assert_reset: bool = True) -> None:
        """Control the hardware reset line signal.

        :param assert_reset: If True the REST signal is asserted (logic low), otherwise the
        reset line is not asserted (third state).
        :raises PEMicroException: The check for loaded PEMicro DLL
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        self._log_debug(f"{'De-' if not assert_reset else ''}Asserting RESET signal")

        self.lib.set_reset_pin_state(0 if assert_reset else 1)

    def read_32bit(self, address: int) -> int:
        """Reads 32 bits of data.

        :param address: The address of memory to read
        :return: An read unsigned long (32 bits)
        :raises PEMicroException: For various kind of issues
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        mem_result = c_ulong()
        value = self.lib.read_32bit_value(0, address, byref(mem_result))

        if mem_result.value != PEMicroMemoryAccessResults.PE_MAR_MEM_OK:
            raise PEMicroException(f"Read 32bit method failed. Result({mem_result.value})")

        return value

    def write_32bit(self, address: int, data: int) -> None:
        """Writes 32 bits of data.

        :param address: The address of memory to read
        :param data: An data to write (32 bits)
        :raises PEMicroException: For various kind of issues
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        mem_result = c_ulong()
        self.lib.write_32bit_value(0, address, data, byref(mem_result))

        if mem_result.value != PEMicroMemoryAccessResults.PE_MAR_MEM_OK:
            raise PEMicroException(f"Write 32bit method failed. Result({mem_result.value})")

    def read_16bit(self, address: int) -> int:
        """Reads 16 bits of data.

        :param address: The address of memory to read
        :return: An read unsigned short (16 bits)
        :raises PEMicroException: For various kind of issues
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        mem_result = c_ulong()
        value = self.lib.read_16bit_value(0, address, byref(mem_result))

        if mem_result.value != PEMicroMemoryAccessResults.PE_MAR_MEM_OK:
            raise PEMicroException(f"Read 16bit method failed. Result({mem_result.value})")

        return value

    def write_16bit(self, address: int, data: int) -> None:
        """Writes 16 bits of data.

        :param address: The address of memory to write
        :param data: An data to write (16 bits)
        :raises PEMicroException: For various kind of issues
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        mem_result = c_ulong()
        self.lib.write_16bit_value(0, address, data, byref(mem_result))

        if mem_result.value != PEMicroMemoryAccessResults.PE_MAR_MEM_OK:
            raise PEMicroException(f"Write 16bit method failed. Result({mem_result.value})")

    def read_8bit(self, address: int) -> int:
        """Reads 8 bits of data.

        :param address: The address of memory to read
        :return: An read unsigned char (8 bits)
        :raises PEMicroException: For various kind of issues
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        mem_result = c_ulong()
        value = self.lib.read_8bit_value(0, address, byref(mem_result))

        if mem_result.value != PEMicroMemoryAccessResults.PE_MAR_MEM_OK:
            raise PEMicroException(f"Read 8bit method failed. Result({mem_result.value})")

        return value

    def write_8bit(self, address: int, data: int) -> None:
        """Writes 8 bits of data.

        :param address: The address of memory to write
        :param data: An data to write (8 bits)
        :raises PEMicroException: For various kind of issues
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        mem_result = c_ulong()
        self.lib.write_8bit_value(0, address, data, byref(mem_result))

        if mem_result.value != PEMicroMemoryAccessResults.PE_MAR_MEM_OK:
            raise PEMicroException(f"Write 8bit method failed. Result({mem_result.value})")

    def read_block(
        self,
        address: int,
        size: int,
        data: bytes,
        access_bit_size: PEMicroMemoryAccessSize = PEMicroMemoryAccessSize.PE_MEM_ACCESS_32BIT,
    ) -> None:
        """Reads block of data.

        :param address: The address of memory block to read
        :param size: The size of memory block to read
        :param data: The data memory block to store read data
        :param access_bit_size: Determines the number of bits read at a time
        :raises PEMicroException: For various kind of issues
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        if size == 0:
            raise PEMicroException("Zero size is not supported")

        if data is None:
            raise PEMicroException("Data buffer must be provided")

        if not isinstance(access_bit_size, PEMicroMemoryAccessSize):
            raise PEMicroException("The access_bit_size has not proper value")

        operation_check = c_byte(size)

        if not self.lib.get_block(0, address, size, access_bit_size, data, operation_check):
            raise PEMicroException("Read block method failed.")

        for data_byte_check in bytes(operation_check):
            if data_byte_check != PEMicroMemoryAccessResults.PE_MAR_MEM_OK:
                raise PEMicroException("Read block method failed.")

    def write_block(
        self,
        address: int,
        size: int,
        data: bytes,
        access_bit_size: PEMicroMemoryAccessSize = PEMicroMemoryAccessSize.PE_MEM_ACCESS_32BIT,
    ) -> None:
        """Writes block of data.

        :param address: The address of memory block to write
        :param size: The size of memory block to write
        :param data: The data memory block with prepared data to write
        :param access_bit_size: Determines the number of bits writes at a time
        :raises PEMicroException: For various kind of issues
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        if size == 0:
            return

        if data is None:
            raise PEMicroException("Data buffer must be provided")

        if not isinstance(access_bit_size, PEMicroMemoryAccessSize):
            raise PEMicroException("The access_bit_size has not proper value")

        operation_check = c_byte(size)

        if not self.lib.put_block(0, address, size, access_bit_size, data, operation_check):
            raise PEMicroException("Write block method failed.")

        for data_byte_check in bytes(operation_check):
            if data_byte_check != PEMicroMemoryAccessResults.PE_MAR_MEM_OK:
                raise PEMicroException("Write block method failed.")

    def load_bin_file(self, filename: str, start_address: int = 0) -> None:
        """Load the binary file into target memory.

        :param filename: File name of the binary image to load.
        :param start_address: Starting address to load.
        :raises PEMicroException: For various kind of issues
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        if filename is None:
            raise PEMicroException("Filename is not specified")

        if self.lib.load_bin_file(filename.encode(), start_address) is False:
            raise PEMicroException("Loading of the binary file failed")

    def load_srec_file(self, filename: str, offset: int = 0) -> None:
        """Load the S-record file into target memory.

        :param filename: File name of the S-record image to load.
        :param offset: Offset for the S-record image to load.
        :raises PEMicroException: For various kind of issues
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        if filename is None:
            raise PEMicroException("Filename is not specified")

        if self.lib.load_srec_file(filename.encode(), offset) is False:
            raise PEMicroException("Loading of the S-record file failed")

    def version(self) -> str:
        """Get version number of the interface library."""
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        version = self.lib.version().decode("utf-8")
        self._log_debug(f"Getting version: {version}")
        return version

    def version_dll(self) -> int:
        """Get version of PEMicro DLL."""
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        version = self.lib.get_dll_version()
        self._log_debug(f"Getting DLL version: {version}")
        return version
