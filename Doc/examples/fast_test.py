#!/usr/bin/env python

import sys
import os
import serial
import struct

def checksum(c):
    inv = ~ord(c[0]) & 0xFF
    high_bit = len(bin(inv)[2:])-1
    mask = 2**high_bit - 1
    checksum = inv & mask
    if len(c) > 1:
        for i in range(1,len(c)):
            inv = ~ord(c[i]) & 0xFF
            xor = checksum ^ inv
            high_bit = len(bin(xor)[2:])-1
            mask = 2**high_bit - 1
            checksum = xor & mask

    return checksum

ser = serial.Serial()
ser.port = "/dev/tty.PL2303-00002006"
#ser.baudrate = 460800
ser.baudrate = 115200
ser.timeout = 1
ser.open()

print "reported baudrate is %d" % ser.baudrate

command = "V"

to_send = command + struct.pack("B", checksum(command))

print "send %s" % to_send

ser.write(to_send)

print "got %s" % ser.read(3)

