#!/usr/bin/env python

import sys
import os
import serial
import struct
import pyfits
import time
import numpy as np

ser = serial.Serial()
ser.port = "/dev/tty.PL2303-00002006"
ser.baudrate = 460800
ser.timeout = 1
ser.open()

print "reported baudrate is %d" % ser.baudrate

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

def getImage(exptime, light=False):
    eres = 1.0e-4
    e = "%06x" % int(exp/eres)
    if light:
        e = e + "00" + "01"
    else:
        e = e + "00" + "00"

    etime = e.decode("hex")
    command = "T" + etime
    to_send = command + struct.pack("B", checksum(command))
    ser.write(to_send)

    print "Exposing %f seconds...." % exptime
    out = "E"
    while out != "D":
        out = ser.read(1)

    print "Getting image...."
    to_send = 'X' + struct.pack("B", checksum('X'))
    ser.write(to_send)
    imag_str = bytearray()

    # not sure why this is needed. not mentioned in document...
    f = ser.read(1)

    # we only use unbinned, full frame
    for i in range(307200/4096):
        npix = 4096
        block_str = ser.read(npix*2)
        cam = ser.read(1)
        lrc = 0
        for b in block_str:
            lrc ^= ord(b)
        imag_str.extend(block_str)
        to_send = 'K' + struct.pack("B", checksum('K'))
        ser.write(to_send)

    # pull these extra bytes out.  also not sure why...
    cam = ser.read(1)
    cam = ser.read(1)
    cam = ser.read(1)
    cam = ser.read(1)
    cam = ser.read(1)

    # this is ugly and there has to be a better way, but it works.
    earr = [z for z in imag_str[::2]]
    oarr = [z for z in imag_str[1::2]]
    arr = []

    for i in range(len(earr)):
        s = struct.pack("BB", earr[i], oarr[i])
        n = struct.unpack("H", s)[0]
        arr.append(n)

    imag = np.array(arr, dtype=np.int32).reshape(480,640)
    return np.flipud(imag)


ndark = 0
exp = 60.0

while True:
    if os.path.isfile("STOP"):
        os.system("rm STOP")
        break

    if ndark == 0:
        print "Getting Dark..."
        dark = getImage(exp, light=False)

    ndark += 1
    print "Getting Light..."
    imag = getImage(exp, light=True)

    now = time.localtime()
    imag -= dark
    filename = time.strftime("AllSky_%Y%m%d_%H%M%S.fits")
    jpg = time.strftime("AllSky_%Y%m%d_%H%M%S.jpg")
    date = time.strftime("%Y/%m/%d")
    sast = time.strftime("%H:%M:%S")
    elabel = "Exposure: %f sec" % exp

    cards = []
    cards.append(pyfits.createCard("DATEOBS", date, "Date of observation"))
    cards.append(pyfits.createCard("TIMEOBS", 
                                   sast, 
                                   "Time of observation (SAST)"))
    cards.append(pyfits.createCard("EXPTIME", exp, "Exposure time (s)"))
    header = pyfits.Header(cards=cards)

    pyfits.writeto(filename, imag, header=header, clobber=True)
    os.system("convert -fill white -normalize \
    -draw 'text 10,20 \"%s\"' \
    -draw 'text 10,40 \"%s\"' \
    -draw 'text 10,60 \"Exptime: %s sec\"' \
    %s %s" % (date, sast, exp, filename, jpg))
    os.system("ln -sf %s AllSkyCurrentImage.JPG" % jpg)
    os.system("ln -sf %s AllSkyCurrentImage.fits" % filename)

    if ndark > 10:
        ndark = 0

    if np.median(imag) > 15000.0:
        exp /= 2.0
        ndark = 0

    if np.median(imag) < 4000.0 and exp < 60.0:
        exp *= 2.0
        ndark = 0
