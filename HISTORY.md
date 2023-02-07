History of PyPEMicro package versions
=====================================

v 0.1.10
-------
 - February 2023
 - Fixed issue when the PyPemicro causes crash of powershell in Windows
 - Reformatted whole code
 - Simplified checking of reopened driver.

v 0.1.9
-------
 - January 2022
 - Just fix bug with self.lib member in case of not loaded PEMicro drivers.

v 0.1.8
-------
 - January 2022
 - Tune app behavior of PyPemicro constructor.

v 0.1.7
-------
 - August 2021
 - Add support for /BSD: FreeBSD, OpenBSD, NetBSD. Thanks to: Tomasz 'CeDeROM' CEDRO <tomek@cedro.info>.

v 0.1.6
-------
 - March 2021
 - Fixed behavior with exception on ussuported OS and some typos.
 - Removed rest comment in PyPemicro exception.

v 0.1.5
-------
 - January 2021
 - Fixed behavior of reset sequention during SWD fault resume.

v 0.1.4
-------
 - January 2021
 - Fixed behavior of "neverending" WAIT acknowledges on SWD. Now the package raised exception in this case.

v 0.1.3
-------
 - November 2020
 - Fixed opening the debug probes libraries under Linux and MacOS

v 0.1.2
-------
 - November 2020
 - Fixed listing the debug probes under Linux and MacOS

v 0.1.1
-------
 - November 2020
 - Fixed list of PEMicro dynamic libraries, for different OS

v 0.1.0
-------
 - October 2020
 - Initial version 
 - Supported most of the functionality of PEMicro probes (ARM controllers)
