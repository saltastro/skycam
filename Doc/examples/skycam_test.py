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
ser.port = "/dev/ttyUSB0"
ser.baudrate = 460800
ser.timeout = 1
ser.open()

print "reported baudrate is %d" % ser.baudrate

command = struct.pack("BB", ord('Z'), 0xFF)
to_send = command + struct.pack("B", checksum(command))

eres = 1.0e-4
exp = int(60.0/eres)

print "exp time 0x%06x" % exp

e = "%06x" % exp

e = e + "00" + "01"
#e = "00" + "00" + e

etime = e.decode("hex")

command = "T" + etime

print "checksum: %s" % checksum(command)

to_send = command + struct.pack("B", checksum(command))

print "sending:"

for c in to_send:
    print c, c.encode("hex")

print ""

ser.write(to_send)

out = "E"

while out != "D":
    out = ser.read(1)
    print "got %s" % out


print "Getting image...."
to_send = 'X' + struct.pack("B", checksum('X'))
ser.write(to_send)

imag_str = bytearray()

f = ser.read(1)

print "Get this at the start: %s" % f

for i in range(307200/4096):
    npix = 4096
    print "Reading block %d...." % i
    block_str = ser.read(npix*2)
    cam = ser.read(1)
    print "Camera checksum is 0x%02x" % ord(cam)
    lrc = 0
    for b in block_str:
       lrc ^= ord(b)
    print "Computed checksum is 0x%02x" % lrc
    imag_str.extend(block_str)
    to_send = 'K' + struct.pack("B", checksum('K'))
    ser.write(to_send)

print "at end..."
cam = ser.read(1)
print "Camera checksum is 0x%02x" % ord(cam)
cam = ser.read(1)
print "Camera checksum is 0x%02x" % ord(cam)
cam = ser.read(1)
print "Camera checksum is 0x%02x" % ord(cam)
cam = ser.read(1)
print "Camera checksum is 0x%02x" % ord(cam)
cam = ser.read(1)
print "Camera checksum is 0x%02x" % ord(cam)

earr = [z for z in imag_str[::2]]
oarr = [z for z in imag_str[1::2]]

arr = []

for i in range(len(earr)):
    s = struct.pack("BB", earr[i], oarr[i])
    n = struct.unpack("H", s)[0]
    arr.append(n)

print arr

imag = np.array(arr, dtype=np.uint16).reshape(480,640)

pyfits.writeto("test.fits", imag, clobber=True)

