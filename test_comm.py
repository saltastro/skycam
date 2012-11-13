#!/usr/bin/env python

import sys
import os
import serial
import struct
import pyfits
import numpy as np

def checksum(c):
    inv = ~ord(c[0]) & 0xFF
    mask = ~(1 << 7)
    checksum = inv & mask
    if len(c) > 1:
        for i in range(1,len(c)):
            inv = ~ord(c[i]) & 0xFF
            xor = checksum ^ inv
            checksum = xor & mask

    return checksum

ser = serial.Serial()
ser.port = "/dev/tty.usbserial-A700dzlT"
ser.baudrate = 460800
ser.timeout = 1
ser.open()
#ser.flush()
#ser.flushInput()

print "reported baudrate is %d" % ser.baudrate

command = "S"
to_send = command + struct.pack("B", checksum(command))
#ser.write(to_send)

command = "K"
to_send = command + struct.pack("B", checksum(command))
print "K command is %s" % to_send
#ser.write(to_send)

command = "E"
to_send = command + struct.pack("B", checksum(command))

print "sending %s" % to_send
ser.write(to_send)
print "got %s" % ser.read(2)
