===========
 PyDAQFlex
===========
Introduction
============

The PyDAQFlex module is a pure Python implementation of Measurement Computing's
DAQFlex command framework (http://www.mccdaq.com/daq-software/DAQFlex.aspx)
for USB data acquisition devices.
It uses PyUSB 1.0 as a backend for USB access and is therefore usable
on all operating systems supported by PyUSB.
PyUSB is currently tested on Windows and Linux,
but should also work on OS X and OpenBSD using libusbx.

*Disclaimer*: PyDAQFlex is NOT in any way affiliated with Measurement Computing or the official
DAQFlex framework.

Status
======

PyDAQFlex does not (yet) provide all the features of DAQFlex and was
only tested on the following devices:

* USB-204
* USB-1608GX-2AO

Installation
============

The easiest way of installation is through setuptools.
On GNU/Linux based systems::

	$ sudo easy_install pydaqflex

or on Windows::

	easy_install pydaqflex

It will automatically install the required dependencies like PyUSB
and the latest release version of PyDAQFlex from PyPi.

Alternatively, PyDAQFlex can be installed manually using the standard
distutils procedure::

	python setup.py install

For installation of PyUSB 1.0 see https://github.com/walac/pyusb

The latest version of libusb (recommended for PyUSB) can be found at
http://libusbx.org/
