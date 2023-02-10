#!/usr/bin/env python
#
# Copyright 2022-2023 NXP
# All rights reserved.
# Visit us at www.nxp.com
#
# SPDX-License-Identifier: BSD-3-Clause

""" Simple tests for PEMicro Python implementation by NXP.
"""

from pypemicro import PyPemicro


def test_library_load():
    """Simple test to be able to load library on current system"""
    assert PyPemicro.get_pemicro_lib()


def test_lib_version():
    """Basic test of dynamic library version."""
    pemicro = PyPemicro()
    version = pemicro.version()
    assert isinstance(version, str)
    assert len(version) > 10


def test_lib_dll_version():
    """Basic test of dynamic library dll version."""
    pemicro = PyPemicro()
    pemicro.lib = PyPemicro.get_pemicro_lib()
    version = pemicro.version_dll()
    assert isinstance(version, int)
    assert version > 1


def test_list_devices():
    """Basic test of listing connected devices."""
    pemicro = PyPemicro()
    devices = pemicro.get_device_list()
    assert isinstance(devices, list)
    assert len(devices) >= 0


def test_list_probes():
    """Basic test of listing connected probes."""
    probes = PyPemicro.list_ports()
    assert isinstance(probes, list)
