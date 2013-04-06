'''
Created on 05.04.2013

@author: dk
'''
import unittest
import time
from numpy import array
import daqflex

class Test_USB_204(unittest.TestCase):
    dev = daqflex.USB_204()


    def test_commands(self):
        '''
        Test if all defined commands are acknowledged by the device.
        '''
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
        raw = [0, 2047.5, 0x0FFF]
        truth = [-10.0, 0.0, 10.0]
        self.assertItemsEqual(self.dev.scale_and_calibrate_data(array(raw),
            - 10, 10, 1, 0), truth)

    def test_ai_scan_block_pulses(self):
        '''
        Test if AISCAN mode works correctly with block readout
        via read_scan_data(), while a test signal is generated on DIO0.
        For this test, DIO0 has to be wired to analog input CH0.
        '''
        for spl in [100, 1000, 10000]:
            self.dev.send_message("DIO{0/0}:DIR=OUT")
            self.dev.send_message("AISCAN:LOWCHAN=0")
            self.dev.send_message("AISCAN:HIGHCHAN=0")
            self.dev.send_message("AISCAN:SAMPLES={0}".format(spl))
            self.dev.send_message("AISCAN:RATE={0}".format(spl * 10))
            self.dev.send_message("AISCAN:XFRMODE=BLOCKIO")
            self.dev.flush_input_data()
            self.dev.send_message("AISCAN:START")
            t_0 = time.time()
            # output pulses to DIO0
            for pulse in range(10):
                while (time.time() < t_0 + 0.01 * (pulse + 0.25)):
                    pass
                self.dev.send_message("DIO{0/0}:VALUE=1")
                while (time.time() < t_0 + 0.01 * (pulse + 0.75)):
                    pass
                self.dev.send_message("DIO{0/0}:VALUE=0")
            dat = self.dev.read_scan_data(spl, spl * 10)
            self.dev.send_message("DIO{0/0}:DIR=IN")
            slope, offset = self.dev.get_calib_data(0)
            dat = self.dev.scale_and_calibrate_data(array(dat), -10, 10,
                                                    slope, offset)
            self.assertTrue(all([-0.5 < dat[i * spl / 10] < 0.5
                                 for i in range(10)]), "Incorrect low values")
            self.assertTrue(all([4.5 < dat[i * spl / 10 + spl / 20] < 5.5
                                 for i in range(10)]), "Incorrect high values")

    def test_ai_scan_continuous_pulses(self):
        '''
        Test if AISCAN mode works correctly with continuous readout,
        while a test signal is generated on DIO0.
        For this test, DIO0 has to be wired to analog input CH0.
        '''
        for spl in [50, 500, 5000, 50000]:
            self.dev.send_message("DIO{0/0}:DIR=OUT")
            self.dev.send_message("AISCAN:LOWCHAN=0")
            self.dev.send_message("AISCAN:HIGHCHAN=0")
            self.dev.send_message("AISCAN:SAMPLES=0")
            self.dev.send_message("AISCAN:RATE={0}".format(spl * 10))
            self.dev.send_message("AISCAN:XFRMODE=BLOCKIO")
            self.dev.flush_input_data()
            dat = []
            self.dev.send_message("AISCAN:START")
            t_0 = time.time()
            self.dev.start_continuous_transfer(spl * 10, 10)#// 5)
            # output pulses to DIO0
            for pulse in range(10):
                while (time.time() < t_0 + 0.01 * (pulse + 0.25)):
                    pass
                self.dev.send_message("DIO{0/0}:VALUE=1")
                while (time.time() < t_0 + 0.01 * (pulse + 0.75)):
                    pass
                self.dev.send_message("DIO{0/0}:VALUE=0")
                dat.extend(self.dev.get_new_bulk_data())
            while (time.time() < t_0 + 0.2):
                pass
            self.dev.stop_continuous_transfer()
            self.dev.send_message("AISCAN:STOP")
            dat.extend(self.dev.get_new_bulk_data())
            self.dev.send_message("DIO{0/0}:DIR=IN")
            slope, offset = self.dev.get_calib_data(0)
            dat = self.dev.scale_and_calibrate_data(array(dat), -10, 10,
                                                    slope, offset)
            self.assertTrue(all([-0.5 < dat[i * spl / 10] < 0.5
                                 for i in range(10)]), "Incorrect low values")
            self.assertTrue(all([4.5 < dat[i * spl / 10 + spl / 20] < 5.5
                                 for i in range(10)]), "Incorrect high values")


suite = unittest.TestLoader().loadTestsFromTestCase(Test_USB_204)
unittest.TextTestRunner(verbosity=2).run(suite)
