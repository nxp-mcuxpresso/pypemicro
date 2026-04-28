#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Unit tests for PyPemicro base class, ARM class, and DSC class.

These tests use mocking to avoid requiring real hardware or native libraries.
"""
from unittest.mock import MagicMock, patch, PropertyMock
import pytest

from pypemicro import (
    PEMicroException,
    PEMicroTransferException,
    PyPemicroBase,
    PyPemicro,
    PyPemicroDsc,
    PEMicroPortType,
    PEMicroInterfaces,
    PEMicroSpecialFeatures,
    PEMicroArmRegisters,
    PEMicroMemoryAccessSize,
    PEMicroMemoryAccessResults,
    PEMicroDscSpecialFeatures,
)


# === Helper to create a mocked instance (bypass __init__ library loading) ===


def _make_base_instance(cls=PyPemicroBase):
    """Create an instance with mocked library, bypassing __init__."""
    instance = object.__new__(cls)
    instance.lib = MagicMock()
    instance._opened = False
    instance.dll_path = None
    instance.opened_debug_file = False
    instance._log_info = MagicMock()
    instance._log_warning = MagicMock()
    instance._log_error = MagicMock()
    instance._log_debug = MagicMock()
    return instance


def _make_arm_instance():
    """Create a PyPemicro ARM instance with mocked library."""
    instance = _make_base_instance(PyPemicro)
    instance.interface = PEMicroInterfaces.SWD
    return instance


def _make_dsc_instance():
    """Create a PyPemicroDsc instance with mocked library."""
    instance = _make_base_instance(PyPemicroDsc)
    return instance


# ==================== Class hierarchy tests ====================


class TestClassHierarchy:
    """Tests for class inheritance structure."""

    def test_pypemicro_inherits_base(self):
        assert issubclass(PyPemicro, PyPemicroBase)

    def test_pypemicro_dsc_inherits_base(self):
        assert issubclass(PyPemicroDsc, PyPemicroBase)

    def test_arm_lib_prefix(self):
        assert PyPemicro.LIB_NAME_PREFIX == "unitacmp"

    def test_dsc_lib_prefix(self):
        assert PyPemicroDsc.LIB_NAME_PREFIX == "unitdsc"

    def test_exception_hierarchy(self):
        assert issubclass(PEMicroTransferException, PEMicroException)


# ==================== Library name tests ====================


class TestLibraryNames:
    """Tests for platform-dependent library name generation."""

    @patch("pypemicro.pemicro_base.platform.system", return_value="Windows")
    @patch("pypemicro.pemicro_base.sys")
    def test_arm_library_name_windows_64(self, mock_sys, mock_platform):
        mock_sys.maxsize = 2**33
        assert PyPemicro.get_library_name() == "unitacmp-64.dll"

    @patch("pypemicro.pemicro_base.platform.system", return_value="Windows")
    @patch("pypemicro.pemicro_base.sys")
    def test_arm_library_name_windows_32(self, mock_sys, mock_platform):
        mock_sys.maxsize = 2**31
        assert PyPemicro.get_library_name() == "unitacmp-32.dll"

    @patch("pypemicro.pemicro_base.platform.system", return_value="Linux")
    @patch("pypemicro.pemicro_base.sys")
    def test_arm_library_name_linux(self, mock_sys, mock_platform):
        mock_sys.maxsize = 2**33
        assert PyPemicro.get_library_name() == "unitacmp-64.so"

    @patch("pypemicro.pemicro_base.platform.system", return_value="Darwin")
    @patch("pypemicro.pemicro_base.sys")
    def test_arm_library_name_macos(self, mock_sys, mock_platform):
        mock_sys.maxsize = 2**33
        assert PyPemicro.get_library_name() == "unitacmp-64.dylib"

    @patch("pypemicro.pemicro_base.platform.system", return_value="Windows")
    @patch("pypemicro.pemicro_base.sys")
    def test_dsc_library_name_windows_64(self, mock_sys, mock_platform):
        mock_sys.maxsize = 2**33
        assert PyPemicroDsc.get_library_name() == "unitdsc-64.dll"

    @patch("pypemicro.pemicro_base.platform.system", return_value="Linux")
    @patch("pypemicro.pemicro_base.sys")
    def test_dsc_library_name_linux(self, mock_sys, mock_platform):
        mock_sys.maxsize = 2**33
        assert PyPemicroDsc.get_library_name() == "unitdsc-64.so"

    @patch("pypemicro.pemicro_base.platform.system", return_value="SomethingUnknown")
    @patch("pypemicro.pemicro_base.sys")
    def test_unknown_os_raises(self, mock_sys, mock_platform):
        mock_sys.maxsize = 2**33
        with pytest.raises(PEMicroException, match="Unable to determinate"):
            PyPemicro.get_library_name()


# ==================== OS name tests ====================


class TestOsName:
    """Tests for user-friendly OS name mapping."""

    @patch("pypemicro.pemicro_base.platform.system", return_value="Windows")
    def test_windows(self, _):
        assert PyPemicroBase.get_user_friendly_os_name() == "Windows"

    @patch("pypemicro.pemicro_base.platform.system", return_value="Linux")
    def test_linux(self, _):
        assert PyPemicroBase.get_user_friendly_os_name() == "Linux"

    @patch("pypemicro.pemicro_base.platform.system", return_value="Darwin")
    def test_macos(self, _):
        assert PyPemicroBase.get_user_friendly_os_name() == "MacOS"


# ==================== Base class connection tests ====================


class TestBaseConnection:
    """Tests for base class connection lifecycle."""

    def test_open_sets_opened(self):
        inst = _make_base_instance()
        inst.lib.open_port_by_identifier.return_value = True
        inst.lib.check_critical_error.return_value = 0
        inst.open("USB1")
        assert inst.opened is True

    def test_open_already_opened_warns(self):
        inst = _make_base_instance()
        inst._opened = True
        inst.open("USB1")
        # Should not call open_port_by_identifier again

    def test_open_connection_fails_raises(self):
        inst = _make_base_instance()
        inst.lib.open_port_by_identifier.return_value = False
        with pytest.raises(PEMicroException, match="Cannot connect"):
            inst.open("USB1")

    def test_open_probe_error_raises(self):
        inst = _make_base_instance()
        inst.lib.open_port_by_identifier.return_value = True
        inst.lib.check_critical_error.return_value = 0x10
        with pytest.raises(PEMicroException, match="Probe error"):
            inst.open("USB1")

    def test_close(self):
        inst = _make_base_instance()
        inst._opened = True
        inst.close()
        assert inst.opened is False
        inst.lib.close_port.assert_called_once()

    def test_close_not_opened(self):
        inst = _make_base_instance()
        inst._opened = False
        inst.close()
        inst.lib.close_port.assert_not_called()

    def test_opened_property(self):
        inst = _make_base_instance()
        assert inst.opened is False
        inst._opened = True
        assert inst.opened is True

    def test_lib_none_raises(self):
        inst = _make_base_instance()
        inst.lib = None
        with pytest.raises(PEMicroException, match="library loader failed"):
            inst.open("USB1")


# ==================== Base class target control tests ====================


class TestBaseTargetControl:
    """Tests for base class target control methods."""

    def test_reset_target(self):
        inst = _make_base_instance()
        inst.lib.target_reset.return_value = True
        inst.reset_target()
        inst.lib.target_reset.assert_called_once()

    def test_reset_target_fails(self):
        inst = _make_base_instance()
        inst.lib.target_reset.return_value = False
        with pytest.raises(PEMicroException, match="Reset target"):
            inst.reset_target()

    def test_halt_target(self):
        inst = _make_base_instance()
        inst.lib.target_halt.return_value = True
        inst.halt_target()
        inst.lib.target_halt.assert_called_once()

    def test_halt_target_fails(self):
        inst = _make_base_instance()
        inst.lib.target_halt.return_value = False
        with pytest.raises(PEMicroException, match="Halt target"):
            inst.halt_target()

    def test_resume_target(self):
        inst = _make_base_instance()
        inst.lib.target_resume.return_value = True
        inst.resume_target()
        inst.lib.target_resume.assert_called_once()

    def test_resume_target_fails(self):
        inst = _make_base_instance()
        inst.lib.target_resume.return_value = False
        with pytest.raises(PEMicroException, match="Resume target"):
            inst.resume_target()

    def test_target_step(self):
        inst = _make_base_instance()
        inst.lib.target_step.return_value = True
        inst.target_step()
        inst.lib.target_step.assert_called_once()

    def test_target_step_fails(self):
        inst = _make_base_instance()
        inst.lib.target_step.return_value = False
        with pytest.raises(PEMicroException, match="Target step"):
            inst.target_step()

    def test_target_check_if_halted(self):
        inst = _make_base_instance()
        inst.lib.target_check_if_halted.return_value = True
        assert inst.target_check_if_halted() is True


# ==================== Base class memory tests ====================


class TestBaseMemory:
    """Tests for base class memory read/write methods."""

    def test_read_32bit(self):
        inst = _make_base_instance()
        inst.lib.read_32bit_value.return_value = 0xDEADBEEF
        # Mock byref to work with the mem_result parameter
        result = inst.read_32bit(0x20000000)
        assert result == 0xDEADBEEF

    def test_write_32bit(self):
        inst = _make_base_instance()
        inst.write_32bit(0x20000000, 0x12345678)
        inst.lib.write_32bit_value.assert_called_once()

    def test_read_16bit(self):
        inst = _make_base_instance()
        inst.lib.read_16bit_value.return_value = 0x1234
        result = inst.read_16bit(0x20000000)
        assert result == 0x1234

    def test_read_8bit(self):
        inst = _make_base_instance()
        inst.lib.read_8bit_value.return_value = 0x42
        result = inst.read_8bit(0x20000000)
        assert result == 0x42


# ==================== Base class utility tests ====================


class TestBaseUtility:
    """Tests for base class utility methods."""

    def test_control_reset_line_assert(self):
        inst = _make_base_instance()
        inst.control_reset_line(assert_reset=True)
        inst.lib.set_reset_pin_state.assert_called_with(0)

    def test_control_reset_line_deassert(self):
        inst = _make_base_instance()
        inst.control_reset_line(assert_reset=False)
        inst.lib.set_reset_pin_state.assert_called_with(1)

    def test_set_debug_frequency(self):
        inst = _make_base_instance()
        inst._opened = True
        inst.set_debug_frequency(1000000)
        inst.lib.set_debug_shift_frequency.assert_called_with(1000000)

    def test_set_debug_frequency_not_opened(self):
        inst = _make_base_instance()
        with pytest.raises(PEMicroException, match="not opened"):
            inst.set_debug_frequency(1000000)

    def test_set_reset_delay(self):
        inst = _make_base_instance()
        inst.set_reset_delay_in_ms(100)
        inst.lib.set_reset_delay_in_ms.assert_called_with(100)

    def test_power_on(self):
        inst = _make_base_instance()
        inst.lib.pe_special_features.return_value = True
        inst.power_on()
        inst.lib.pe_special_features.assert_called()

    def test_power_off(self):
        inst = _make_base_instance()
        inst.lib.pe_special_features.return_value = True
        inst.power_off()
        inst.lib.pe_special_features.assert_called()

    def test_version(self):
        inst = _make_base_instance()
        inst.lib.version.return_value = b"PEMicro Test v1.0"
        assert inst.version() == "PEMicro Test v1.0"

    def test_version_dll(self):
        inst = _make_base_instance()
        inst.lib.get_dll_version.return_value = 104
        assert inst.version_dll() == 104

    def test_lib_none_raises_on_methods(self):
        """Test that methods raise when lib is None."""
        inst = _make_base_instance()
        inst.lib = None
        with pytest.raises(PEMicroException):
            inst.reset_target()
        with pytest.raises(PEMicroException):
            inst.halt_target()
        with pytest.raises(PEMicroException):
            inst.resume_target()
        with pytest.raises(PEMicroException):
            inst.version()

    def test_get_lib_filename(self):
        record = {"path": "/some/path", "name": "lib.dll"}
        result = PyPemicroBase.get_lib_filename(record)
        assert "lib.dll" in result

    def test_get_newest_lib_filename(self):
        lib_list = [
            {"path": "/a", "name": "lib.dll", "version_num": 100},
            {"path": "/b", "name": "lib.dll", "version_num": 200},
            {"path": "/c", "name": "lib.dll", "version_num": 150},
        ]
        result = PyPemicroBase.get_newest_lib_filename(lib_list)
        assert "/b" in result

    def test_get_newest_lib_filename_empty_raises(self):
        with pytest.raises(PEMicroException):
            PyPemicroBase.get_newest_lib_filename([])

    def test_get_newest_lib_filename_none_raises(self):
        with pytest.raises(PEMicroException):
            PyPemicroBase.get_newest_lib_filename(None)


# ==================== Debug file tests ====================


class TestDebugFile:
    """Tests for debug file operations."""

    def test_open_debug_file(self):
        inst = _make_base_instance()
        inst.open_debug_file("test.txt")
        assert inst.opened_debug_file is True

    def test_close_debug_file(self):
        inst = _make_base_instance()
        inst.opened_debug_file = True
        inst.close_debug_file()
        assert inst.opened_debug_file is False
        inst.lib.close_debug_file.assert_called_once()


# ==================== ARM-specific tests ====================


class TestArmSpecific:
    """Tests for ARM-specific PyPemicro class."""

    def test_close_flushes_queued_data(self):
        inst = _make_arm_instance()
        inst._opened = True
        inst.lib.pe_special_features.return_value = True
        inst.close()
        # Verify flush was called before close_port
        assert inst.lib.pe_special_features.called

    def test_connect_swd(self):
        inst = _make_arm_instance()
        inst._opened = True
        inst.lib.pe_special_features.return_value = True
        inst.connect(PEMicroInterfaces.SWD, 1000000)
        assert inst.interface == PEMicroInterfaces.SWD

    def test_connect_jtag(self):
        inst = _make_arm_instance()
        inst._opened = True
        inst.lib.pe_special_features.return_value = True
        inst.connect(PEMicroInterfaces.JTAG, 500000)
        assert inst.interface == PEMicroInterfaces.JTAG

    def test_connect_not_opened_raises(self):
        inst = _make_arm_instance()
        inst._opened = False
        with pytest.raises(PEMicroException, match="not opened"):
            inst.connect()

    def test_write_ap_register(self):
        inst = _make_arm_instance()
        inst._opened = True
        inst.lib.pe_special_features.return_value = True
        with patch.object(inst, "last_swd_status", return_value=0x04):
            inst.write_ap_register(apselect=0, addr=0xFC, value=0x12345678)

    def test_read_ap_register(self):
        inst = _make_arm_instance()
        inst._opened = True
        inst.lib.pe_special_features.return_value = True
        with patch.object(inst, "last_swd_status", return_value=0x04):
            result = inst.read_ap_register(apselect=0, addr=0xFC)
            assert isinstance(result, int)

    def test_write_dp_register(self):
        inst = _make_arm_instance()
        inst._opened = True
        inst.lib.pe_special_features.return_value = True
        with patch.object(inst, "last_swd_status", return_value=0x04):
            inst.write_dp_register(addr=0x04, value=0x50000000)

    def test_read_dp_register(self):
        inst = _make_arm_instance()
        inst._opened = True
        inst.lib.pe_special_features.return_value = True
        with patch.object(inst, "last_swd_status", return_value=0x04):
            result = inst.read_dp_register(addr=0x00)
            assert isinstance(result, int)

    def test_ap_register_not_opened_raises(self):
        inst = _make_arm_instance()
        inst._opened = False
        with pytest.raises(PEMicroException, match="opened"):
            inst.write_ap_register(0, 0, 0)
        with pytest.raises(PEMicroException, match="opened"):
            inst.read_ap_register(0, 0)

    def test_dp_register_not_opened_raises(self):
        inst = _make_arm_instance()
        inst._opened = False
        with pytest.raises(PEMicroException, match="opened"):
            inst.write_dp_register(0, 0)
        with pytest.raises(PEMicroException, match="opened"):
            inst.read_dp_register(0)

    def test_flush_any_queued_data(self):
        inst = _make_arm_instance()
        inst._opened = True
        inst.lib.pe_special_features.return_value = True
        inst.flush_any_queued_data()

    def test_flush_not_opened_raises(self):
        inst = _make_arm_instance()
        inst._opened = False
        with pytest.raises(PEMicroException, match="not active"):
            inst.flush_any_queued_data()

    def test_get_mcu_register(self):
        inst = _make_arm_instance()
        inst.lib.get_mcu_register.return_value = True
        result = inst.get_mcu_register(PEMicroArmRegisters.PE_ARM_REG_PC)
        assert isinstance(result, int)

    def test_get_mcu_register_invalid_raises(self):
        inst = _make_arm_instance()
        with pytest.raises(PEMicroException, match="Invalid register"):
            inst.get_mcu_register(999)

    def test_set_mcu_register(self):
        inst = _make_arm_instance()
        inst.lib.set_mcu_register.return_value = True
        inst.set_mcu_register(PEMicroArmRegisters.PE_ARM_REG_R0, 0x12345678)

    def test_set_device_name(self):
        inst = _make_arm_instance()
        inst._opened = False
        inst.lib.pe_special_features.return_value = True
        inst.set_device_name("Cortex-M33")

    def test_set_device_name_already_opened_raises(self):
        inst = _make_arm_instance()
        inst._opened = True
        with pytest.raises(PEMicroException, match="already opened"):
            inst.set_device_name("Cortex-M33")

    def test_get_device_list(self):
        inst = _make_arm_instance()
        inst.lib.pe_special_features.return_value = True
        # The c_char_p return value will be mocked
        result = inst.get_device_list()
        assert isinstance(result, list)

    def test_last_swd_status(self):
        inst = _make_arm_instance()
        inst.lib.pe_special_features.return_value = True
        result = inst.last_swd_status()
        assert isinstance(result, int)


# ==================== DSC-specific tests ====================


class TestDscSpecific:
    """Tests for DSC-specific PyPemicroDsc class."""

    def test_connected_to_debug_cable_property(self):
        inst = _make_dsc_instance()
        assert inst.connected_to_debug_cable is False
        inst._opened = True
        assert inst.connected_to_debug_cable is True

    def test_connect_to_debug_cable(self):
        inst = _make_dsc_instance()
        inst.lib.open_port_by_identifier.return_value = True
        inst.lib.check_critical_error.return_value = 0
        inst.connect_to_debug_cable("USB1")
        assert inst.opened is True

    def test_jtag_init(self):
        inst = _make_dsc_instance()
        inst._opened = True
        inst.lib.pe_special_features.return_value = True
        inst.jtag_init()
        inst.lib.pe_special_features.assert_called_with(
            PEMicroDscSpecialFeatures.PE_DSC_JTAG_INIT, True, 0, 0, 0, 0, 0
        )

    def test_jtag_init_not_connected_raises(self):
        inst = _make_dsc_instance()
        inst._opened = False
        with pytest.raises(PEMicroException, match="Not connected"):
            inst.jtag_init()

    def test_jtag_idle(self):
        inst = _make_dsc_instance()
        inst._opened = True
        inst.lib.pe_special_features.return_value = True
        inst.jtag_idle(5)
        inst.lib.pe_special_features.assert_called_with(
            PEMicroDscSpecialFeatures.PE_DSC_JTAG_IDLE, True, 5, 0, 0, 0, 0
        )

    def test_jtag_idle_not_connected_raises(self):
        inst = _make_dsc_instance()
        inst._opened = False
        with pytest.raises(PEMicroException, match="Not connected"):
            inst.jtag_idle()

    def test_write_ir(self):
        inst = _make_dsc_instance()
        inst._opened = True
        inst.lib.pe_special_features.return_value = True
        result = inst.write_ir(0x04, 8)
        assert isinstance(result, int)

    def test_write_ir_not_connected_raises(self):
        inst = _make_dsc_instance()
        inst._opened = False
        with pytest.raises(PEMicroException, match="Not connected"):
            inst.write_ir(0x04, 8)

    def test_write_dr(self):
        inst = _make_dsc_instance()
        inst._opened = True
        inst.lib.pe_special_features.return_value = True
        data = bytearray(b"\x01\x02\x03\x04")
        result = inst.write_dr(32, data)
        assert isinstance(result, bytearray)
        assert len(result) == 4

    def test_write_dr_failure_returns_empty(self):
        inst = _make_dsc_instance()
        inst._opened = True
        inst.lib.pe_special_features.return_value = False
        data = bytearray(b"\x01\x02\x03\x04")
        result = inst.write_dr(32, data)
        assert result == bytearray()

    def test_write_dr_not_connected_raises(self):
        inst = _make_dsc_instance()
        inst._opened = False
        with pytest.raises(PEMicroException, match="Not connected"):
            inst.write_dr(32, bytearray(4))

    def test_target_set_reset_pin_assert(self):
        inst = _make_dsc_instance()
        inst.target_set_reset_pin(False)
        inst.lib.set_reset_pin_state.assert_called_with(0)

    def test_target_set_reset_pin_release(self):
        inst = _make_dsc_instance()
        inst.target_set_reset_pin(True)
        inst.lib.set_reset_pin_state.assert_called_with(1)

    def test_lib_none_raises(self):
        inst = _make_dsc_instance()
        inst.lib = None
        with pytest.raises(PEMicroException):
            inst.jtag_init()
        with pytest.raises(PEMicroException):
            inst.write_ir(0, 0)
        with pytest.raises(PEMicroException):
            inst.write_dr(0, bytearray())
        with pytest.raises(PEMicroException):
            inst.target_set_reset_pin(True)


# ==================== Constants tests ====================


class TestConstants:
    """Tests for constant values."""

    def test_arm_special_features(self):
        assert PEMicroSpecialFeatures.PE_ARM_SET_COMMUNICATIONS_MODE == 0x44000001

    def test_dsc_special_features(self):
        assert PEMicroDscSpecialFeatures.PE_DSC_JTAG_INIT == 0x40000400
        assert PEMicroDscSpecialFeatures.PE_DSC_WRITE_IR == 0x40000401
        assert PEMicroDscSpecialFeatures.PE_DSC_WRITE_DR == 0x40000402
        assert PEMicroDscSpecialFeatures.PE_DSC_JTAG_IDLE == 0x40000403

    def test_port_types(self):
        assert PEMicroPortType.AUTODETECT == 99
        assert PEMicroPortType.USB_MULTILINK == 3

    def test_interfaces(self):
        assert PEMicroInterfaces.SWD == 1
        assert PEMicroInterfaces.JTAG == 0
        assert PEMicroInterfaces.get_str(PEMicroInterfaces.SWD) == "SWD"
        assert PEMicroInterfaces.get_str(PEMicroInterfaces.JTAG) == "JTAG"

    def test_memory_access_size(self):
        assert PEMicroMemoryAccessSize.PE_MEM_ACCESS_8BIT == 1
        assert PEMicroMemoryAccessSize.PE_MEM_ACCESS_16BIT == 2
        assert PEMicroMemoryAccessSize.PE_MEM_ACCESS_32BIT == 4
