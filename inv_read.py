#!/usr/bin/python
import crc16
import usb.core
import usb.util
import logging
import json
import requests
import time, traceback, sys

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

DELAY = 10

UPDATE_URL = 'http://localhost/emoncms/input/post.json?node=2&apikey=77f5d5679778fb15c066607589d188ab&json='


def sendAndReceiveCommand(cmd):
    cmd = conditionCommand(cmd)
    dev = acquireDevice()
    if(dev is False):
        raise IOError("Could not acquire device.")
    try:
        sendCommand(dev, cmd)
        result = getResult(dev)
        if (validateResult(result)):
            return result[1:-2];
        raise IOError("Result[" + ''.join(str(e) for e in result) + "] validation failed. Will retry.")
    finally:
        releaseDevice(dev)


def sendCommand(dev, cmd):
        bytesSent = dev.ctrl_transfer(0x21, 0x9, 0x200, 0, cmd)
        logging.debug("Sent commmand to device.")
        if(bytesSent == len(cmd)):
            return True
        return False

def to_bytes(n, length):
    return ('%%0%dx' % (length << 1) % n).decode('hex')[-length:]

def conditionCommand(cmd):
    cmd = cmd.encode('utf-8')
    crc = to_bytes(crc16.crc16xmodem(cmd), 2)
    cmd = cmd + crc
    cmd = cmd + b'\r'
    while len(cmd) < 8:
        cmd = cmd + b'\0'
    return cmd

def getResult(dev, timeout=100):
    endpoint = dev[0][(0, 0)][0]
    res = []
    calls = 0
    while '\r' not in res and calls < 50:
        try:
            res.extend([i for i in dev.read(endpoint.bEndpointAddress, endpoint.wMaxPacketSize, timeout) if i != 0x00])
        except usb.core.USBError as e:
            if e.errno == 110: #Timeout
                break
            else:
                raise
    calls += 1
    logging.debug("Read from device.")
    return res[0:-1]

def validateResult(result):
    if not result:
        return False
    firstPart = result[0:-2]
    lastPart = result[-2:]
    crc = hex(crc16.crc16xmodem(str(bytearray(firstPart))))
    lastPart = hex(int(str(bytearray(lastPart)).encode('hex'), 16))
    if(crc == lastPart):
        return True
    return False

def acquireDevice():
    # decimal vendor and product values
    dev = usb.core.find(idVendor=0x0665, idProduct=0x5161)
    if(dev is None):
        return False
    # first endpoint
    interface = 0
    # if the OS kernel already claimed the device, which is most likely true
    # thanks to http://stackoverflow.com/questions/8218683/pyusb-cannot-set-configuration
    if dev.is_kernel_driver_active(interface) is True:
      # tell the kernel to detach
      dev.detach_kernel_driver(interface)
      time.sleep(1)
      # claim the device
      usb.util.claim_interface(dev, interface)
    dev.set_configuration()
    dev.reset()
    logging.debug("Acquired device.")
    return dev

def releaseDevice(dev):
    # release the device
    usb.util.release_interface(dev, 0)
    # reattach the device to the OS kernel
    dev.attach_kernel_driver(0)
    logging.debug("Released device.")


def performUsbTalk(command):
    collected = 0
    attempts = 5
    while collected < attempts :
        try:
            logging.debug("Performing USB talk...")
            data = ''.join(chr(e) for e in sendAndReceiveCommand(command))
            collected += 1
            return data
        except usb.core.USBError as e:
            data = None
            if e.args == ('Operation timed out',):
                logging.debug("Communication timed out.")
                time.sleep(1)
                continue
        except IOError as e:
            logging.debug("IOError: " + e.message + ". Retrying.")
            time.sleep(1)
            continue

def main():
    data = performUsbTalk("QPIGS").split(" ")
    output = {}
    output['InvV'] = float(data[2])
    output['InvPApparent'] = float(data[4])
    output['InvPActual'] = float(data[5])
    output['InvLoadPercent'] = int(data[6])
    output['BattV'] = float(data[8])
    output['BattChrargeI'] = float(data[9])
    output['BattCapacity'] = int(data[10])
    output['BattDischargeI'] = int(data[15])
    output['SolarPvP'] = int(data[19])
    output['SolarPvI'] = int(data[12])
    output['SolarPvV'] = float(data[13])

    updated_url = UPDATE_URL + json.dumps(output)
    requests.get(updated_url)

if __name__ == "__main__":
    while True:
        try:
            main()
            sys.exit(0)
        except Exception as e:
            logging.error("Unknown exception: " + e.message)
            print (traceback.format_exc())
            pass
        # Sleep and repeat
        time.sleep(DELAY)
