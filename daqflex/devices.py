# coding=utf-8
"""
Python library to use data acquisition devices from Measurement Computing
with the DAQFlex command language.

Copyright (c) 2013, David Kiliani <mail@davidkiliani.de>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""
# pylint: disable=C0103

import errno
import array
import codecs
import collections
import pkg_resources
import time
import usb
from .utils import PollingThread


class MCCDevice(object):
    """
    Base class for a MCC USB device.
    """
    id_vendor = 0x09db
    id_product = None
    max_counts = None
    fpga_image = None

    def __init__(self, serial_number=None):
        """
        Connect to a device with a given product id and serial number.
        :param serial_number: serial number of the device to connect to
        (default = None, use the first device regardless of serial number)
        """
        if self.id_product is None:
            raise ValueError('id_product not defined')
        # find our device
        if serial_number is None:
            self.dev = usb.core.find(idVendor=self.id_vendor,
                                     idProduct=self.id_product)
        else:
            self.dev = usb.core.find(idVendor=self.id_vendor,
                                     idProduct=self.id_product,
                                     serial_number=serial_number)
        # was it found?
        if self.dev is None:
            raise ValueError('Device not found')
        self.dev.set_configuration()
        self._intf = self.__get_interface()
        self._ep_in = self.__get_bulk_endpoint(usb.util.ENDPOINT_IN)
        self._ep_out = self.__get_bulk_endpoint(usb.util.ENDPOINT_OUT)
        if self._ep_in:
            self._bulk_packet_size = self._ep_in.wMaxPacketSize
        self._polling_thread = None
        self.data_buffer = None
        # does this model require FPGA firmware loading?
        if self.fpga_image:
            # Check FPGA configuration status
            ret = self.send_message('?DEV:FPGACFG')
            if ret == 'DEV:FPGACFG=CONFIGMODE':
                # FPGA has not yet been loaded
                # Send FW upload unlock code 0xAD
                self.send_message('DEV:FPGACFG=0xAD')
                # retrieve FPGA image from Python package
                rbf = pkg_resources.resource_string(__name__, self.fpga_image)
                # transmit image 64 bytes at a time using command 0x51
                for i in range(0, len(rbf), 64):
                    msg = rbf[i:i + 64]
                    self.dev.ctrl_transfer(usb.TYPE_VENDOR + usb.ENDPOINT_OUT,
                                           0x51, 0, 0, msg)
                # minimum pause seems to be necessary after sending the firmware
                time.sleep(0.25)
            ret = self.send_message('?DEV:FPGACFG')
            if ret != 'DEV:FPGACFG=CONFIGURED':
                raise IOError("Could not configure FPGA")

    @classmethod
    def find_serial_numbers(cls):
        """Return list of serial numbers of attached devices."""
        return [d.serial_number for d in usb.core.find(
            idVendor=cls.id_vendor, idProduct=cls.id_product, find_all=True)]

    def send_message(self, message):
        """
        Send a command message to the device via control transfer
        and return the device response.
        :param message: the command string to send
        """
        # Some devices (e.g. USB-1608G series) expect a null-terminated string
        message += '\0'

        try:
            assert self.dev.ctrl_transfer(
                usb.TYPE_VENDOR + usb.ENDPOINT_OUT, 0x80, 0, 0,
                message.upper().encode('ascii')) == len(message)
        except AssertionError:
            raise IOError("Could not send message")
        except usb.core.USBError:
            raise IOError("Send failed, possibly wrong command?")
        ret = self.dev.ctrl_transfer(usb.TYPE_VENDOR + usb.ENDPOINT_IN,
                                     0x80, 0, 0, 64)
        return codecs.decode(ret, 'ascii').rstrip(chr(0))

    def read_scan_data(self, length, rate):
        """
        Read the data generated by a AISCAN bulk transfer.
        :param length: the number of values to read
        :param rate: the sample rate of the AISCAN command in Hz
        """
        timeout = int(self._bulk_packet_size * 1e3 / 2 / rate) + 10
        data = array.array('H')
        while True:
            packet = None
            try:
                packet = self._ep_in.read(self._bulk_packet_size, timeout)
            except usb.core.USBError as err:
                if err.errno != errno.ETIMEDOUT:
                    raise err
            if (packet is None) or (len(packet) == 0):
                break
            data.fromstring(packet)
            if len(data) >= length:
                break
        return data

    def flush_input_data(self):
        """Read and discard all remaining data from the bulk input."""
        while True:
            try:
                packet = self._ep_in.read(self._bulk_packet_size, 20)
            except usb.core.USBError:
                break
            if len(packet) == 0:
                break

    def start_continuous_transfer(self, rate, buf_size, packet_size=None):
        """
        Start an asynchronous data transfer to read AISCAN values.
        :param rate: the sample rate of the AISCAN command in Hz
        :param buf_size: the maximum number of data packets in the buffer
        :param packet_size: the size of a data packet in bytes
        (default = None, automatic determination based on rate)
        """
        if packet_size is None:
            packet_size = (rate // 1000 + 1) * 64
        self.data_buffer = collections.deque(maxlen=buf_size)
        self._polling_thread = PollingThread(self._ep_in, self.data_buffer,
                                             packet_size, rate)
        self._polling_thread.start()

    def stop_continuous_transfer(self):
        """
        Stop the asynchronous data transfer and wait for the data collection
        to finish.
        """
        if self._polling_thread is not None:
            self._polling_thread.shutdown.set()
            self._polling_thread.join()
            self._polling_thread = None

    def get_new_bulk_data(self, wait=False):
        """
        Return all continuous transfer data in the buffer.
        :param wait: if True, block until new data is available
        """
        if wait and self._polling_thread is not None:
            self._polling_thread.new_data.wait()
        data = array.array("H")
        while self.data_buffer:
            data.extend(self.data_buffer.popleft())
        if self._polling_thread is not None:
            self._polling_thread.new_data.clear()
        return data

    def get_calib_data(self, channel):
        """
        Query the calibration parameters slope and offset for a given channel.
        The returned values are only valid for the currently selected
        voltage range.
        :param channel: the analog input channel to calibrate
        """
        slope = float(self.send_message(
            "?AI{{{0}}}:SLOPE".format(channel)).split('=')[1])
        offset = float(self.send_message(
            "?AI{{{0}}}:OFFSET".format(channel)).split('=')[1])
        return slope, offset

    @classmethod
    def scale_and_calibrate_data(cls, data, min_voltage, max_voltage, calib):
        """
        Apply scaling and calibration to calculate voltages from raw data.
        :param data: the raw data (number or numpy array)
        :param min_voltage: selected minimum voltage of the AI channel
        :param max_voltage: selected maximum voltage of the AI channel
        :param calib: calibration slope and offset as a tuple
        (see get_calib_data)
        """
        slope, offset = calib
        full_scale = max_voltage - min_voltage
        cal_data = data * float(slope) + offset
        return (cal_data / cls.max_counts) * full_scale + min_voltage

    def __get_interface(self):
        """Get the USB interface descriptor."""
        cfg = self.dev.get_active_configuration()
        intf_number = cfg[(0, 0)].bInterfaceNumber
        alternate_setting = usb.control.get_interface(self.dev, intf_number)
        return usb.util.find_descriptor(cfg, bInterfaceNumber=intf_number,
                                        bAlternateSetting=alternate_setting)

    def __get_bulk_endpoint(self, direction):
        """
        Get the USB endpoint for bulk read or write.
        :param direction: ENDPOINT_IN or ENDPOINT_OUT
        """

        def ep_match(endp):
            """Find an endpoint with descriptor = 5 and correct direction"""
            return (usb.util.endpoint_direction(endp.bEndpointAddress) ==
                    direction) and (endp.bDescriptorType == 5)

        return usb.util.find_descriptor(self._intf, custom_match=ep_match)


class USB_7202(MCCDevice):
    """USB-7202 card"""
    max_counts = 0xFFFF
    id_product = 0x00F2


class USB_7204(MCCDevice):
    """USB-7204 card"""
    max_counts = 0x0FFF
    id_product = 0x00F0


class USB_2001_TC(MCCDevice):
    """USB-2001-TC card"""
    max_counts = 1
    id_product = 0x00F9


class USB_1608FS_Plus(MCCDevice):
    """USB-1608FS-Plus card"""
    max_counts = 0xFFFF
    id_product = 0x00EA


class USB_1608G(MCCDevice):
    """USB-1608G card"""
    fpga_image = 'firmware/USB_1608G.rbf'
    max_counts = 0xFFFF
    id_product = 0x0110


class USB_1608GX(USB_1608G):
    """USB-1608GX card"""
    max_counts = 0xFFFF
    id_product = 0x0111


class USB_1608GX_2AO(USB_1608G):
    """USB-1608GX-2AO card"""
    max_counts = 0xFFFF
    id_product = 0x0112


class USB_201(MCCDevice):
    """USB-204 card"""
    max_counts = 0x0FFF
    id_product = 0x0113


class USB_204(MCCDevice):
    """USB-204 card"""
    max_counts = 0x0FFF
    id_product = 0x0114
