#!/usr/bin/env python
#
# Copyright (c) 2020 P&E Microcomputer Systems, Inc
# All rights reserved.
# Visit us at www.pemicro.com
#
# Copyright 2020-2023 NXP
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
"""PEMicro Python implementation by NXP.

The basics of the code is comming from original PEMicro version.
"""
import logging
import os.path
import platform
import sys
from typing import Any, Dict, List
from ctypes import (
    CDLL,
    c_bool,
    c_ulong,
    c_ushort,
    c_char_p,
    c_byte,
    c_void_p,
    byref,
)
from .pemicro_const import (
    PEMicroPortType,
    PEMicroSpecialFeatures,
    PEMicroSpecialFeaturesSwdStatus,
    PEMicroMemoryAccessResults,
    PEMicroMemoryAccessSize,
    PEMicroArmRegisters,
    PEMicroInterfaces,
)


class PEMicroException(Exception):
    """The base PEMicro implementation exception."""


class PEMicroTransferException(PEMicroException):
    """PEMicro Transfer exception."""


logger = logging.getLogger(__name__)


class PyPemicro:
    """PEMicro Debug probe Python class."""

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

    @staticmethod
    def get_library_name() -> str:
        """Get library name.

        Just help function to get right library name depending on used OS.
        :return: Name of library to use on current running system.
        """
        libs = {
            "Windows": {"32bit": "unitacmp-32.dll", "64bit": "unitacmp-64.dll"},
            "Linux": {"32bit": "unitacmp-64.so", "64bit": "unitacmp-64.so"},
            "Darwin": {"32bit": "unitacmp-64.dylib", "64bit": "unitacmp-64.dylib"},
            "FreeBSD": {"32bit": "unitacmp-64.so", "64bit": "unitacmp-64.so"},
            "OpenSD": {"32bit": "unitacmp-64.so", "64bit": "unitacmp-64.so"},
            "NetBSD": {"32bit": "unitacmp-64.so", "64bit": "unitacmp-64.so"},
        }

        pointer_size = "64bit" if sys.maxsize > 2**32 else "32bit"
        system_name = platform.system()
        if system_name not in libs.keys():
            raise PEMicroException(
                f"Unable to determinate running operation system ({system_name})"
            )

        return libs[system_name][pointer_size]  # type: ignore

    @staticmethod
    def _load_pemicro_lib_info(dll_path: str, lib_name: str) -> Dict:
        """Get the PEMicro library info.

        Help function to try load and fill up information
        about the Pemicro DLL on specified path.
        :param dll_path: path to look for the library.
        :param lib_name: name of the library.
        :return: Fill up information about libraray on specified path
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
            )
        return lib_info

    @staticmethod
    def get_pemicro_lib_list(dll_path: str = None, search_generic: bool = True) -> List:
        """Gets the description list of PEMicro DLLs.

        :param dll_path: User way to add specific a DLL path.
        :param search_generic: If it's True, the engine search also in general places in system.
        :return: The List of search results.
        :raises PEMicroException: Various kind of issues
        """
        # Get the name of PEMicro dynamic library
        lib_name = PyPemicro.get_library_name()

        library_dlls = []
        if dll_path is not None:
            try:
                library_dlls.append(PyPemicro._load_pemicro_lib_info(dll_path, lib_name))
            except PEMicroException:
                pass

        if search_generic:
            # Look in System Folders
            try:
                library_dlls.append(PyPemicro._load_pemicro_lib_info("", lib_name))
            except PEMicroException:
                pass
            # Look in the folder with .py file
            try:
                library_dlls.append(
                    PyPemicro._load_pemicro_lib_info(os.path.dirname(__file__), lib_name)
                )
            except PEMicroException:
                pass
            # Look in a local library storage snapshot
            try:
                os_utility_path = os.path.join("libs", PyPemicro.get_user_friendly_os_name())
                library_dlls.append(
                    PyPemicro._load_pemicro_lib_info(
                        os.path.join(os.path.dirname(__file__), os_utility_path),
                        lib_name,
                    )
                )
            except PEMicroException:
                pass

        if len(library_dlls) == 0:
            logger.debug("There is no PEMICRO library.")

        return library_dlls

    @staticmethod
    def open_library(file_name: str) -> CDLL:
        """Open PEMicro library with specified full path.

        :param file_name: File Name of PEMicro dynamic library.
        :return: Fill up information about libraray and library itself
        :raises PEMicroException: Cannot load the library
        """
        if file_name is None:
            raise PEMicroException("The libray file name MUST be specified.")

        try:
            # Open the Pemicro library and
            dll = CDLL(file_name)
        except (FileNotFoundError, OSError) as exc:
            raise PEMicroException(
                f"Cannot load the PEMICRO library({file_name}). " + f"Error({str(exc)})"
            )

        if dll is None:
            raise PEMicroException("The PEMicro library load failed.")

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

        # void close_port(void);
        #  No parameters and return value

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

        # void close_debug_file(char *filename)

        # unsigned long read_32bit_value(unsigned long memory_access_tag, unsigned long address,
        #                                mem_result *optional_mem_result)
        dll.read_32bit_value.argtypes = [c_ulong, c_ulong, c_void_p]
        dll.read_32bit_value.restype = c_ulong

        # void write_32bit_value(unsigned long memory_access_tag, unsigned long address,
        #                        unsigned long datum,
        #                        mem_result *optional_mem_result)
        dll.write_32bit_value.argtypes = [c_ulong, c_ulong, c_ulong, c_void_p]

        # unsigned short read_16bit_value(unsigned long memory_access_tag, unsigned long address,
        #                                 mem_result *optional_mem_result)
        dll.read_16bit_value.argtypes = [c_ulong, c_ulong, c_void_p]
        dll.read_16bit_value.restype = c_ushort

        # void write_16bit_value(unsigned long memory_access_tag, unsigned long address,
        #                        unsigned long datum,
        #                        mem_result *optional_mem_result)
        dll.write_16bit_value.argtypes = [c_ulong, c_ulong, c_ulong, c_void_p]

        # unsigned char read_8bit_value(unsigned long memory_access_tag, unsigned long address,
        #                               mem_result *optional_mem_result)
        dll.read_8bit_value.argtypes = [c_ulong, c_ulong, c_void_p]
        dll.read_8bit_value.restype = c_byte

        # void write_8bit_value(unsigned long memory_access_tag, unsigned long address,
        #                       unsigned long datum,
        #                       mem_result *optional_mem_result)
        dll.write_8bit_value.argtypes = [c_ulong, c_ulong, c_ulong, c_void_p]

        # bool get_block(unsigned int memory_access_tag,
        #                unsigned int address,
        #                unsigned int num_bytes,
        #                unsigned int access_sizing,
        #                unsigned char *buffer_ptr,
        #                unsigned char *optional_error_ptr)
        dll.get_block.argtypes = [
            c_ulong,
            c_ulong,
            c_ulong,
            c_ulong,
            c_char_p,
            c_char_p,
        ]
        dll.get_block.restype = c_bool

        # bool put_block(unsigned int memory_access_tag,
        #                unsigned int address,
        #                unsigned int num_bytes,
        #                unsigned int access_sizing,
        #                unsigned char *buffer_ptr,
        #                unsigned char *optional_error_ptr)
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

        # bool get_mcu_register(unsigned long register_access_tags, unsigned long reg_num, unsigned long *reg_value)
        dll.get_mcu_register.argtypes = [c_ulong, c_ulong, c_void_p]
        dll.get_mcu_register.restype = c_bool

        # bool set_mcu_register(unsigned long register_access_tags, unsigned long reg_num, unsigned long reg_value)
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

    @staticmethod
    def get_lib_filename(lib_record: Dict) -> str:
        """Get the filename from the library dictionary record.

        Convert the dictionary record to filename.
        :param lib_record: Input dictionary record.
        :return: File name path in string.
        """
        return os.path.join(lib_record["path"], lib_record["name"])

    @staticmethod
    def get_newest_lib_filename(lib_list: List) -> str:
        """Gets the latest version of PEMicro library from list.

        :param lib_list: List of PEMicro libraries in system
                         (for example it can be get by get_pemicro_lib_list() method).
        :return: The absolute path to PEMicro library.
        :raises PEMicroException: Various kind of issues
        """
        if lib_list is None:
            raise PEMicroException("The input list must exists")

        # Get the best one library from the list now
        if len(lib_list) == 0:
            raise PEMicroException("Unable to find any usable library in the system!")

        # Find the latest version from all loaded libraries
        ver_ix = 0
        for count, item in enumerate(lib_list):
            if item["version_num"] > lib_list[ver_ix]["version_num"]:
                ver_ix = count

        return PyPemicro.get_lib_filename(lib_list[ver_ix])

    @staticmethod
    def get_pemicro_lib(dll_path: str = None, get_newest: bool = True) -> CDLL:
        """Gets the best possible PEMicro DLL.

        :param dll_path: User way to force the DLL path.
        :param get_newest: If it's true the latest version of DLL is used.
        :return: The PEMicro CDLL Python object.
        :raises PEMicroException: Various kind of issues
        """
        try:
            libs_list = PyPemicro.get_pemicro_lib_list(dll_path=dll_path)
            if len(libs_list) == 0:
                raise PEMicroException("There is any suitable library for this OS.")
            if get_newest:
                filename = PyPemicro.get_newest_lib_filename(libs_list)
            else:
                filename = PyPemicro.get_lib_filename(libs_list[0])
        except PEMicroException as exc:
            raise PEMicroException(str(exc))

        return PyPemicro.open_library(filename)

    @staticmethod
    def list_ports() -> List:
        """Get list of all connected PEMicro probes.

        :return: List of all connected probes to system.
        :raises PEMicroException: The library is not loaded.
        """
        try:
            lib = PyPemicro.get_pemicro_lib()
        except PEMicroException as exc:
            raise PEMicroException(str(exc))

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
            logger.info(f"No hardware detected locally.")
        i = 0
        for port in ports:
            logger.info(f"{i:>2}: {port['id']} => {port['description']}")
            i += 1

    @staticmethod
    def list_ports_name() -> None:
        """List to logger (info level) the all connected PEMicro probe names.

        :raises PEMicroException: Usually that the port is not opened.
        """
        try:
            lib = PyPemicro.get_pemicro_lib()
        except PEMicroException as exc:
            raise PEMicroException(str(exc))

        num_ports = lib.get_enumerated_number_of_ports(PEMicroPortType.AUTODETECT)
        if num_ports == 0:
            logger.info("No hardware detected locally.")
        for i in range(1, num_ports + 1):
            logger.info(
                lib.get_port_descriptor_short(PEMicroPortType.AUTODETECT, i).decode("utf-8")
            )

        del lib

    def __init__(
        self,
        dll_path: str = None,
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
        # Initialize the basic objects
        self._opened = False
        self.dll_path = dll_path
        self.lib = None
        self.lib = PyPemicro.get_pemicro_lib(dll_path)

        self.interface = PEMicroInterfaces.SWD
        self.opened_debug_file = False

        # register logging objects
        self._log_info = log_info or logger.info
        self._log_warning = log_war or logger.warning
        self._log_error = log_err or logger.error
        self._log_debug = log_debug or logger.debug

        # Set as a default the path to this package
        self.set_application_files_directory(os.path.dirname(__file__))

    def _special_features(
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
        :raises PEMicroException: VArious kind of problems.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        if not isinstance(featurenum, PEMicroSpecialFeatures):
            raise PEMicroException("Invalid argument to do special feature")

        if self.lib.pe_special_features(featurenum, fset, par1, par2, par3, ref1, ref2) is False:
            raise PEMicroException("The special feature command hasn't accepted")

    def set_application_files_directory(self, dir: str) -> None:
        """Set the application files directory.

        :param dir: Path to PEMicro application files
        :raises PEMicroException: Invalid directory.
        """

        if not isinstance(dir, str) or not os.path.exists(dir):
            raise PEMicroException("Invalid input directory.")

        if (
            self.lib.pe_special_features(
                PEMicroSpecialFeatures.PE_SET_DEFAULT_APPLICATION_FILES_DIRECTORY,
                True,
                0,
                0,
                0,
                c_char_p((dir).encode("utf-8")),
                None,
            )
            is False
        ):
            raise PEMicroException("The special feature command hasn't accepted")

    def reenumerate_all_port_types(self) -> None:
        """Reenumerate of usable interface for PEMicro.

        This call rescans the USB and Ethernet ports to enumerate
        all the P&E hardware interfaces.
        raises PEMicroException: Various kind of problems.
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
            # USB1 is a generic identifier which will select the first autodetected USB pemicro device
            port_name = c_char_p("USB1".encode("utf-8"))
        else:
            # This identifier can be the debug hardware's IP address, assigned name,
            #  serial number, or generic identifier (USB1, ETHERNET1)
            port_name = c_char_p(debug_hardware_name_ip_or_serialnum.encode("utf-8"))

        if not self.lib.open_port_by_identifier(port_name):
            raise PEMicroException("Cannot connect to debug probe")

        self._opened = True

        # Connect and initialize the P&E hardware interface. This does not attempt to reset the target.
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
            # Do nothing if .open() has not been called.
            return

        # Close any open connections to hardware
        self._special_features(PEMicroSpecialFeatures.PE_ARM_FLUSH_ANY_QUEUED_DATA)

        if self.opened_debug_file:
            self.close_debug_file()

        if self.lib is not None:
            self.lib.close_port()

        self._opened = False

    def __del__(self) -> None:
        """Action for deleting the class instance."""
        # Close the possibly opened connection
        self.close()
        # Unload the library if necessary
        if self.lib is not None:
            del self.lib
            self.lib = None

    def open_debug_file(self, filename: str = "log_pemicro_comm.txt") -> None:
        """Log the debug communication into file.

        This allows the BDM communication traffic to be recorded
        to an encrypted debug file. This is for P&E’s use in diagnosing
        problems in the field. This call will start recording all commands
        and target responses of debug commands to a specified file. The
        filename should be specified with a full path.
        :param filename: File name to be used to store the debug communication.
        :raises PEMicroException: Various kind of problems.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        self.lib.open_debug_file(filename.encode())

        self.opened_debug_file = True

    def close_debug_file(self) -> None:
        """Close the debug log file.

        This routine is to be used in conjunction with “open_debug_file( )”
        This routine closes an open debug file (writing all data to disk).
        :raises PEMicroException: Various kind of problems.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        self.lib.close_debug_file()

        self.opened_debug_file = False

    def power_on(self) -> None:
        """Power on target."""
        self._log_debug(f"Power on target")
        self._special_features(PEMicroSpecialFeatures.PE_PWR_TURN_POWER_ON)

    def power_off(self) -> None:
        """Power off target."""
        self._log_debug(f"Power off target")
        self._special_features(PEMicroSpecialFeatures.PE_PWR_TURN_POWER_OFF)

    def reset_target(self) -> None:
        """Reset target.

        :raises PEMicroException: Various kind of exceptions.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        self._log_debug(f"Reset target")
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

        Causes the CPU to execute a single assembly (machine) instruction at the current program counter.

        :raises PEMicroException: Various kind of exceptions.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        if self.lib.target_step() is False:
            raise PEMicroException("Target step failed")

    def halt_target(self) -> None:
        """Halt target.

        Tries to place the CPU into the background mode via a special sequence.
        Used to halt execution in a CPU currently running. For example, may be
        used to halt the CPU after a resume command.

        :raises PEMicroException: Various kind of exceptions.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        self._log_debug(f"Halt target")

        if self.lib.target_halt() is not True:
            raise PEMicroException("Halt target sequence failed")

    def resume_target(self) -> None:
        """Resume target.

        :raises PEMicroException: Various kind of exceptions.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        self._log_debug(f"Resume target")

        if self.lib.target_resume() is not True:
            raise PEMicroException("Resume target sequence failed")

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

    def set_reset_delay_in_ms(self, delay: int) -> None:
        """Set the Reset delay.

        :raises PEMicroException: Check to load library.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")

        self._log_debug(f"Reset target delay has been set to {delay}ms")
        self.lib.set_reset_delay_in_ms(delay)

    def flush_any_queued_data(self) -> None:
        """Function flush any possible queued data in DLL->Probe->Target.

        :raises PEMicroException: Check to active connection.
        """
        if not self._opened:
            raise PEMicroException("The connection is not active")

        self._log_debug(f"All queued data has been flushed")
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

    def get_device_list(self, search_string: str = None) -> List:
        """Get the device list.

        :param search_string: The participial string to filter results.
        :raises PEMicroException: Check to opened connection.
        :return: List of all devices
        """
        MAX_BUFF_LEN = 1000000
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        ret_val = c_char_p(bytes(MAX_BUFF_LEN))

        try:
            self._special_features(
                PEMicroSpecialFeatures.PE_GENERIC_GET_DEVICE_LIST,
                par1=MAX_BUFF_LEN - 1,
                ref1=ret_val,
                ref2=None if search_string is None else search_string.encode("utf-8"),
            )
        except PEMicroException as exc:
            raise PEMicroException(f"It is impossible to retrive PEMicro device list:{str(exc)}.")

        return ret_val.value.decode().split(",")

    def version(self) -> str:
        """Get version number of the interface library."""
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        version = self.lib.version().decode("utf-8")
        self._log_debug(f"Getting version: {version}")
        return version

    def version_dll(self) -> int:
        """Get version of PEMicro DLL.

        The DLL version as an unsigned short (word), such that a DLL
         version 1.04 would have a return value of decimal 104.
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        version = self.lib.get_dll_version()
        self._log_debug(f"Getting DLL version: {version}")
        return version

    def connect(self, interface: PEMicroInterfaces = PEMicroInterfaces.SWD, shift_speed: int = 1000000) -> None:  # type: ignore
        """Connect to target.

        :param interface: Select the communication interface.
        :param shift_speed: Set the communication speed.
        :raises PEMicroException: Various reasons for interrupt connect operation.
        """
        # connectToDebugCable must be used first to connect to the debug hardware
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
            raise PEMicroException(f"Failed to connect to target: {str(exc)}")

        self._log_info(
            f"Connected to target over {PEMicroInterfaces.get_str(interface)} with clock {shift_speed}Hz"
        )

    def set_debug_frequency(self, freq: int) -> None:
        """Set debug interface frequency.

        :raises PEMicroException: When any problems occurs
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        if not self._opened:
            raise PEMicroException("The communication interface is not opened")
        self._log_debug(f"The communication speed has been switched to {freq}Hz")

        # Set Shift Rate
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

        Reads 32 bits of data from a specified memory address location.
        If reading more than one consecutive value from memory, the get_block command is recommended.
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

        Writes 32 bits of data to a specified memory address location.
        If writing more than one consecutive value to memory, the put_block command is recommended.
        :param address: The address of memory to read
        :param data: An data to write (32 bits)
        :raises PEMicroException: For various kind of issues
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        mem_result = c_ulong()
        value = self.lib.write_32bit_value(0, address, data, byref(mem_result))

        if mem_result.value != PEMicroMemoryAccessResults.PE_MAR_MEM_OK:
            raise PEMicroException(f"Write 32bit method failed. Result({mem_result.value})")

    def read_16bit(self, address: int) -> int:
        """Reads 16 bits of data.

        Reads 16 bits of data from a specified memory address location.
        If reading more than one consecutive value from memory, the get_block command is recommended.
        :param address: The address of memory to read
        :return: An read unsigned long (16 bits)
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
        """Reads 16 bits of data.

        Writes 16 bits of data to a specified memory address location.
        If writing more than one consecutive value to memory, the put_block command is recommended.
        :param address: The address of memory to read
        :param data: An data to write (16 bits)
        :raises PEMicroException: For various kind of issues
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        mem_result = c_ulong()
        value = self.lib.write_16bit_value(0, address, data, byref(mem_result))

        if mem_result.value != PEMicroMemoryAccessResults.PE_MAR_MEM_OK:
            raise PEMicroException(f"Write 16bit method failed. Result({mem_result.value})")

    def read_8bit(self, address: int) -> int:
        """Reads 8 bits of data.

        Reads 8 bits of data from a specified memory address location.
        If reading more than one consecutive value from memory, the get_block command is recommended.
        :param address: The address of memory to read
        :return: An read unsigned long (8 bits)
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
        """Reads 8 bits of data.

        Writes 8 bits of data to a specified memory address location.
        If writing more than one consecutive value to memory, the put_block command is recommended.
        :param address: The address of memory to read
        :param data: An data to write (8 bits)
        :raises PEMicroException: For various kind of issues
        """
        if self.lib is None:
            raise PEMicroException("Library is not loaded")
        mem_result = c_ulong()
        value = self.lib.write_8bit_value(0, address, data, byref(mem_result))

        if mem_result.value != PEMicroMemoryAccessResults.PE_MAR_MEM_OK:
            raise PEMicroException(f"Write 8bit method failed. Result({mem_result.value})")

    def read_block(
        self,
        address: int,
        size: int,
        data: bytes,
        access_bit_size: PEMicroMemoryAccessSize = PEMicroMemoryAccessSize.PE_MEM_ACCESS_32BIT,
    ) -> None:  # type: ignore
        """Reads block of data.

        This routine allows a faster read rate of the target memory than reading individual memory locations,
        especially across the USB or Ethernet medium. Data is read starting at the "address" and placed in
        the PC buffer.
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
            raise PEMicroException(f"Read block method failed.")

        for data_byte_check in operation_check:
            if data_byte_check != PEMicroMemoryAccessResults.PE_MAR_MEM_OK:
                raise PEMicroException(f"Read block method failed.")

    def write_block(
        self,
        address: int,
        size: int,
        data: bytes,
        access_bit_size: PEMicroMemoryAccessSize = PEMicroMemoryAccessSize.PE_MEM_ACCESS_32BIT,
    ) -> None:  # type: ignore
        """Writes block of data.

        This routine allows a faster write rate of the target memory than writing individual memory locations,
        especially across the USB or Ethernet medium. Data, placed in the PC buffer, is write starting
        at the "address".
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
            raise PEMicroException(f"Write block method failed.")

        for data_byte_check in operation_check:
            if data_byte_check != PEMicroMemoryAccessResults.PE_MAR_MEM_OK:
                raise PEMicroException(f"Write block method failed.")

    def load_bin_file(self, filename: str, start_address: int = 0) -> None:
        """Load the binary file into target memory.

        Loads binary data from a specified file into the target processor’s memory.
        This call is designed to write to RAM and does not directly support FLASH memory.
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

        Loads S-record data from a specified file into the target processor’s memory.
        This call is designed to write to RAM and does not directly support FLASH memory.
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
                    # Connect and initialize the P&E hardware interface. This does not attempt to reset the target.
                    self.lib.reset_hardware_interface()

                try:
                    self.reset_target()
                except:
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
            f"Writing into AP register: Addr: 0x{addr:08X}, Value:{value}, 0x{value:08X}, now?{now}"
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
            f"Read AP register: Addr: 0x{addr:08X}, Value:{ret_val.value}, 0x{ret_val.value:08X}"
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
            f"Writing into DP register: Addr: 0x{addr:08X}, Value:{value}, 0x{value:08X}, now?:{now}"
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
            f"Read DP register: Addr: 0x{addr:08X}, Value:{ret_val.value}, 0x{ret_val.value:08X}"
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
