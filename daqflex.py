'''
Created on 04.04.2013

@author: dk
'''
# pylint: disable=C0103

import usb, array, struct, codecs

class MCCDevice(object):
    '''
    Base class for a MCC USB device.
    '''
    id_vendor = 0x09db
    id_product = None
    def __init__(self, serial_number=None):
        '''
        Constructor
        '''
        if self.id_product is None:
            raise ValueError('idProduct not defined')
        # find our device
        if serial_number is None:
            self.dev = usb.core.find(idVendor=self.id_vendor,
                                     idProduct=self.id_product)
        else:
            dev_list = usb.core.find(idVendor=self.id_vendor,
                idProduct=self.id_product, find_all=True)
            dev_list = [d for d in dev_list if usb.util.get_string(d,
                256, d.iSerialNumber) == serial_number]
            self.dev = dev_list[0] if dev_list else None
        # was it found?
        if self.dev is None:
            raise ValueError('Device not found')
        self.dev.set_configuration()
        self.intf = self.__get_interface()
        self.ep_in = self.__get_endpoint_in()
        self.bulk_packet_size = 64
    def send_message(self, message):
        '''
        Send a command message to the device via control transfer
        and return the device response.
        :param message: the command string to send
        '''
        try:
            assert self.dev.ctrl_transfer(usb.TYPE_VENDOR + usb.ENDPOINT_OUT,
                0x80, 0, 0, message.upper().encode('ascii')) == len(message)
        except AssertionError:
            raise IOError("Could not send message")
        except usb.core.USBError:
            raise IOError("Send failed, possibly wrong command?")
        ret = self.dev.ctrl_transfer(usb.TYPE_VENDOR + usb.ENDPOINT_IN,
                                     0x80, 0, 0, 64)
        return codecs.decode(ret, 'ascii').rstrip('\0')
    def read_scan_data(self, length, rate):
        timeout = int(self.bulk_packet_size * 1e3 / 2 / rate) + 10
        data = array.array('B')
        while (True):
            try:
                packet = self.ep_in.read(self.bulk_packet_size, timeout)
            except usb.core.USBError as err:
                print len(packet)
                pass#raise err
            data.extend(packet)
            if (len(packet) == 0) or (len(data) > length * 2):
                break
        return struct.unpack("=" + "H" * (len(data) / 2), data)[:length]
    def flush_input_data(self):
        pass
    def start_continuous_transfer(self, rate, buffer, samps, delay):
        pass
    def stop_continuous_transfer(self):
        pass
    def cal_data(self, data, slope, offset):
        pass
    def scale_and_calibrate_data(self, data, min_voltage, max_voltage,
                                 scale, offset):
        pass
    def __get_interface(self):
        cfg = self.dev.get_active_configuration()
        intf_number = cfg[(0, 0)].bInterfaceNumber
        alternate_setting = usb.control.get_interface(self.dev, intf_number)
        return usb.util.find_descriptor(cfg, bInterfaceNumber=intf_number,
            bAlternateSetting=alternate_setting)
    def __get_endpoint_in(self):
        '''Get the USB endpoint for bulk read'''
        def ep_match(endp):
            '''Find an endpoint with descriptor = 5 and dir = IN'''
            return (usb.util.endpoint_direction(endp.bEndpointAddress) ==
                usb.util.ENDPOINT_IN) and (endp.bDescriptorType == 5)
        return usb.util.find_descriptor(self.intf, custom_match=ep_match)

class USB_7202(MCCDevice):
    '''USB-7202 card'''
    max_counts = 0xFFFF
    id_product = 0x00F2
class USB_7204(MCCDevice):
    '''USB-7204 card'''
    max_counts = 0x0FFF
    id_product = 0x00F0
class USB_2001_TC(MCCDevice):
    '''USB-2001-TC card'''
    max_counts = 1
    id_product = 0x00F9
class USB_1608FS_Plus(MCCDevice):
    '''USB-1608FS-Plus card'''
    max_counts = 0xFFFF
    id_product = 0x00EA
class USB_1608G(MCCDevice):
    '''USB-1608G card'''
    max_counts = 0xFFFF
    id_product = 0x0110
class USB_1608GX(USB_1608G):
    '''USB-1608GX card'''
    max_counts = 0xFFFF
    id_product = 0x0111
class USB_1608GX_2AO(USB_1608G):
    '''USB-1608GX-2AO card'''
    max_counts = 0xFFFF
    id_product = 0x0112
class USB_201(MCCDevice):
    '''USB-204 card'''
    max_counts = 0x0FFF
    id_product = 0x0113
class USB_204(MCCDevice):
    '''USB-204 card'''
    max_counts = 0x0FFF
    id_product = 0x0114

if __name__ == "__main__":
    import time
    import pylab
    dev = USB_204("01854CA1")
    dev.send_message("DIO{0/0}:DIR=OUT")
    #dev.send_message("AISCAN:RESET")
    dev.send_message("AISCAN:LOWCHAN=0")
    dev.send_message("AISCAN:HIGHCHAN=0")
    dev.send_message("AISCAN:RATE=1000")
    dev.send_message("AISCAN:SAMPLES=2000")
    dev.send_message("AISCAN:XFRMODE=BLOCKIO")
    print dev.send_message("?AISCAN:EXTPACER")
    print dev.send_message("AISCAN:START")
    for x in range(8):
        dev.send_message("DIO{0/0}:VALUE=1")
        time.sleep(1.0 / 8 ** 2 * x)
        dev.send_message("DIO{0/0}:VALUE=0")
        time.sleep(1.0 / 8 ** 2 * (8 - x))
    dat = dev.read_scan_data(2000, 1000)
    dev.send_message("DIO{0/0}:DIR=IN")
    print dat
    print len(dat)
    pylab.plot(dat)
    pylab.show()
