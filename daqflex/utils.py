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

import array
import errno
from threading import Thread, Event
import usb


class PollingThread(Thread):
    """Thread for asynchronous, continuous data retrieval."""
    def __init__(self, endpoint, data_buf, packet_size, rate):
        super(PollingThread, self).__init__()
        self.endpoint = endpoint
        self._packet_size = packet_size
        self.data_buffer = data_buf
        self.rate = rate
        self.shutdown = Event()
        self.new_data = Event()

    def run(self):
        timeout = int(self._packet_size * 1e3 / 2 / self.rate) + 10
        while not self.shutdown.is_set():
            packet = None
            try:
                packet = self.endpoint.read(self._packet_size, timeout)
            except usb.core.USBError as err:
                if err.errno != errno.ETIMEDOUT:
                    raise err
            if (packet is None) or (len(packet) == 0):
                break
            # convert to uint16 and put whole packet into buffer
            data = array.array("H")
            data.fromstring(packet)
            self.data_buffer.append(data)
            # notify listeners of new data
            self.new_data.set()