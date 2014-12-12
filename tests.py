# coding=utf-8
"""
Test suite for the daqflex module.

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

import unittest
import time
from numpy import array
import daqflex


class TestUsb204(unittest.TestCase):
    dev = daqflex.USB_204()

    def test_commands(self):
        """
        Test if all defined commands are acknowledged by the device.
        """
        commands = ["?AI",
                    "?DEV:MFGSER"]
        for cmd in commands:
            resp = self.dev.send_message(cmd)
            self.assertEqual(resp.split('=')[0], cmd.lstrip('?'),
                             "No acknowledgement for " + cmd)
            if cmd[0] == '?':
                self.assertTrue(bool(resp.split('=')[1]),
                                "No return value for " + cmd)

    def test_calibrate_data(self):
        """
        Test if data calibration works.
        """
        raw = [0, 2047.5, 0x0FFF]
        truth = [-10.0, 0.0, 10.0]
        for a, b in zip(self.dev.scale_and_calibrate_data(array(raw), -10,
                                                          10, (1, 0)), truth):
            self.assertEqual(a, b)

    def test_ai_scan_block_pulses(self):
        """
        Test if AISCAN mode works correctly with block readout
        via read_scan_data(), while a test signal is generated on DIO0.
        For this test, DIO0 has to be wired to analog input CH0.
        """
        t_start = time.time()
        t_x = 0.1
        pulses = 10
        for spl in [100, 1000, 10000]:
            self.dev.send_message("DIO{0/0}:DIR=OUT")
            self.dev.send_message("AISCAN:LOWCHAN=0")
            self.dev.send_message("AISCAN:HIGHCHAN=0")
            self.dev.send_message("AISCAN:SAMPLES={0}".format(spl))
            self.dev.send_message("AISCAN:RATE={0}".format(spl / t_x))
            self.dev.send_message("AISCAN:XFRMODE=BLOCKIO")
            self.dev.flush_input_data()
            self.dev.send_message("AISCAN:START")
            # test readout while sampling
            self.dev.read_scan_data(spl, spl / t_x)
            self.dev.flush_input_data()
            self.dev.send_message("AISCAN:START")
            t_0 = time.time()
            # output pulses to DIO0
            for pulse in range(pulses):
                while time.time() < t_0 + t_x / pulses * (pulse + 0.25):
                    time.sleep(1e-4)
                self.dev.send_message("DIO{0/0}:VALUE=1")
                while time.time() < t_0 + t_x / pulses * (pulse + 0.75):
                    time.sleep(1e-4)
                self.dev.send_message("DIO{0/0}:VALUE=0")
            # readout after sampling
            dat = self.dev.read_scan_data(spl, spl / t_x)
            self.dev.send_message("DIO{0/0}:DIR=IN")
            calib = self.dev.get_calib_data(0)
            dat = self.dev.scale_and_calibrate_data(array(dat), -10, 10, calib)
            self.assertEqual(len(dat), spl, "Incorrect number of values")
            self.assertTrue(all([-0.5 < dat[i * spl / pulses] < 0.5
                                 for i in range(pulses)]),
                            "Incorrect low values")
            self.assertTrue(all([4.5 < dat[i * spl / pulses +
                                           spl / (2 * pulses)] < 5.5
                                 for i in range(pulses)]),
                            "Incorrect high values")
        self.assertLess(time.time(), t_start + 1.5, "Test took too much time")

    def test_ai_scan_continuous_pulses(self):
        """
        Test if AISCAN mode works correctly with continuous readout,
        while a test signal is generated on DIO0.
        For this test, DIO0 has to be wired to analog input CH0.
        """
        t_start = time.time()
        t_x = 0.25
        pulses = 10
        for spl in [100, 1000, 10000, 100000]:
            self.dev.send_message("DIO{0/0}:DIR=OUT")
            self.dev.send_message("AISCAN:LOWCHAN=0")
            self.dev.send_message("AISCAN:HIGHCHAN=0")
            self.dev.send_message("AISCAN:SAMPLES=0")
            self.dev.send_message("AISCAN:RATE={0}".format(spl / t_x))
            self.dev.send_message("AISCAN:XFRMODE=BLOCKIO")
            self.dev.flush_input_data()
            dat = []
            self.dev.start_continuous_transfer(int(spl / t_x), 100)
            t_0 = time.time()
            self.dev.send_message("AISCAN:START")
            # output pulses to DIO0
            for pulse in range(pulses):
                while time.time() < t_0 + t_x / pulses * (pulse + 1.25):
                    time.sleep(1e-4)
                self.dev.send_message("DIO{0/0}:VALUE=1")
                while time.time() < t_0 + t_x / pulses * (pulse + 1.75):
                    time.sleep(1e-4)
                self.dev.send_message("DIO{0/0}:VALUE=0")
                dat.extend(self.dev.get_new_bulk_data())
            while time.time() < t_0 + t_x * 1.2:
                time.sleep(1e-4)
            self.dev.stop_continuous_transfer()
            self.dev.send_message("AISCAN:STOP")
            dat.extend(self.dev.get_new_bulk_data())
            self.dev.send_message("DIO{0/0}:DIR=IN")
            calib = self.dev.get_calib_data(0)
            dat = self.dev.scale_and_calibrate_data(array(dat), -10, 10, calib)
            self.assertGreaterEqual(len(dat), spl,
                                    "Insufficient number of values")
            self.assertTrue(all([-0.5 < dat[(i + 1) * spl / pulses] < 0.5
                                 for i in range(pulses)]),
                            "Incorrect low values")
            self.assertTrue(all([4.5 < dat[(i + 1) * spl / pulses +
                                           spl / (2 * pulses)] < 5.5
                                 for i in range(pulses)]),
                            "Incorrect high values")
        self.assertLess(time.time(), t_start + 1.5, "Test took too much time")


suite = unittest.TestLoader().loadTestsFromTestCase(TestUsb204)
unittest.TextTestRunner(verbosity=2).run(suite)
