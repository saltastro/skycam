#!/usr/bin/env python
"""
                AllSky340

Base class and utilities for operating an SBIG AllSky340 allsky camera.  
Tested and used with the monochrome model only.  Color version will require 
some modifications. The camera is based on the SG-4 autoguider so this could 
easily be adapted to that as well.  The information used here was gleaned from:

http://sbig.impulse.net/pdffiles/SBIG%20SG-4%20&%20AllSky-340(C)%20Serial%20Interface%20Specification.pdf

Currently only supporting 1x1 binning and either full (640x480) or cropped
(512x480).  

Author                     Version             Date
--------------------------------------------------------
TE Pickering                 0.1             20130114

TODO
--------------------------------------------------------
- add support for SG-4 and color version.  split into basic class for SG-4
  that the AllSky340 classes can inherit from.
  
- figure out how to do simultaneous expose and readout...

Updates
--------------------------------------------------------

"""


import sys
import os
import serial
import struct
import pyfits
import time
import numpy as np
import logging


def emit_colored_ansi(fn):
    def new(*args):
        levelno = args[1].levelno
        if(levelno >= 50):
            color = '\x1b[31m'  # red
        elif(levelno >= 40):
            color = '\x1b[31m'  # red
        elif(levelno >= 30):
            color = '\x1b[33m'  # yellow
        elif(levelno >= 20):
            color = '\x1b[32m'  # green
        elif(levelno >= 10):
            color = '\x1b[35m'  # pink
        else:
            color = '\x1b[0m'  # normal
        args[1].levelname = color + args[1].levelname + '\x1b[0m'  # normal
        return fn(*args)
    return new

# Initialize logger
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
cam_log = logging.getLogger()
fh = logging.FileHandler("skycam.log")
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter("%(asctime)s: %(levelname)s - %(message)s"))
cam_log.addHandler(fh)
ch = logging.StreamHandler()
f = logging.Formatter("%(levelname)s: %(message)s")
ch.setFormatter(f)
logging.StreamHandler.emit = emit_colored_ansi(logging.StreamHandler.emit)

class AllSky340:
    def __init__(self, port="/dev/tty.usbserial-A700dzlT",
                    baudrate=460800, timeout=1):
        self.ser = serial.Serial()
        self.ser.port = port
        self.ser.baudrate = baudrate
        self.ser.timeout = timeout
        self.ser.open()

    def get_baudrate(self):
        return self.ser.baudrate

    def checksum(self, c):
        inv = ~ord(c[0]) & 0xFF
        mask = ~(1 << 7)
        checksum = inv & mask
        if len(c) > 1:
            for i in range(1, len(c)):
                inv = ~ord(c[i]) & 0xFF
                xor = checksum ^ inv
                checksum = xor & mask
        return checksum

    def command(self, cmd, nbytes):
        to_send = cmd + struct.pack("B", self.checksum(cmd))
        self.ser.write(to_send)
        if nbytes > 0:
            return self.ser.read(nbytes)
        else:
            return True

    def ping(self):
        resp = self.command("E", 2)
        cam_log.info("Pinged camera and received response of %s" % resp)
        return resp[1]

    def open_shutter(self):
        cam_log.info("Opening camera shutter")
        return self.command("O", 0)

    def close_shutter(self):
        cam_log.info("Closing camera shutter")
        return self.command("C", 0)

    def shutter_off(self):
        cam_log.info("De-energizing camera shutter")
        return self.command("K", 0)

    def abort_image(self):
        cam_log.info("Aborting current exposure")
        return self.command("A", 0)

    def firmware(self):
        resp = self.command("V", 2)
        minor = ord(resp[1])
        major = ord(resp[0])
        if major >= 8:
            ver = "T"
            major -= 8
        else:
            ver = "V"
        version = "%s%i.%i" % (ver, major, minor)
        cam_log.info("Camera firmware: %s (raw) %s (formatted)" % (resp, version))
        return version

    def set_baudrate(self, baud):
        old_baud = self.ser.baudrate
        cam_log.info("Setting camera baudrate to %d" % baud)
        cmds = {9600:   "B0",
                19200:  "B1",
                38400:  "B2",
                57600:  "B3",
                115200: "B4",
                230400: "B5",
                460800: "B6"}
        if baud not in cmds.keys():
            cam_log.error("NOT A VALID BAUDRATE!")
            return False
        else:
            cmd = cmds[baud]
            self.command(cmd, 0)
            self.ser.baudrate = baud
            resp = self.ser.read(2)
            cam_log.info("Baudrate set, got response of %s" % resp)
            resp = self.command("Test", 7)
            cam_log.info("Tested new baudrate and got response of %s" % resp)
            if resp[:-1] == "TestOk":
                cam_log.info("Camera accepted new baudrate.")
                self.command("k", 0)
                return True
            else:
                cam_log.warn("Camera did not accept new baudrate. Resetting to previous rate.")
                self.ser.baudrate = old_baud
                return False
    
    def heater_on(self):
        """
        per communication with SBIG, the heater is wired to the X+ guide relay
        on the camera.  use the 'force guide relays' command to toggle it
        """
        cmd = 'g' + struct.pack("B", 1)
        cam_log.info("Turning camera heater on")
        self.command(cmd, 0)
        return True
        
    def heater_off(self):
        cmd = 'g' + struct.pack("B", 0)
        cam_log.info("Turning camera heater off")
        self.command(cmd, 0)
        return True

    def shutter_chop_on(self):
        """
        this is an undocumented command that was provided by SBIG via
        email.  it's simply U plus 0x01 (on) or 0x00 (off).
        """
        cmd = 'U' + struct.pack("B", 1)
        cam_log.info("Enabling chopping shutter mode.")
        self.command(cmd, 0)
        return True
        
    def shutter_chop_off(self):
        cmd = 'U' + struct.pack("B", 0)
        cam_log.info("Disabling chopping shutter mode.")
        self.command(cmd, 0)
        return True
                
    def getImage(self, exptime, light=False, cropped=False):
        eres = 1.0e-4
        e = "%06x" % int(exptime / eres)
        if light:
            e = e + "00" + "01"
        else:
            e = e + "00" + "00"

        etime = e.decode("hex")
        command = "T" + etime
        to_send = command + struct.pack("B", self.checksum(command))
        self.ser.write(to_send)

        if cropped:
            crop = "cropped"
        else:
            crop = "full"
            
        if light:
            imtype = "light"
        else:
            imtype = "dark"
            
        cam_log.info("Exposing %s %s image for %f seconds...." %
                     (crop, imtype, exptime))

        out = "E"
        s = ""
        while out != "D":
            out = self.ser.read(1)

        cam_log.info("Transferring image from camera....")
        to_send = 'X' + struct.pack("B", self.checksum('X'))
        self.ser.write(to_send)
        imag_str = bytearray()

        # not sure why this is needed. not mentioned in document...
        f = self.ser.read(1)

        # we only use unbinned and either full or cropped
        if cropped:
            nbytes = 245760
        else:
            nbytes = 307200
            
        for i in range(nbytes / 4096):
            npix = 4096
            block_str = self.ser.read(npix * 2)
            cam = self.ser.read(1)
            lrc = 0
            for b in block_str:
                lrc ^= ord(b)

            # i'm just blindly grabbing the data here. need to update
            # to check returned checksum and re-try as needed. comms are
            # pretty reliable in our case, though.
            imag_str.extend(block_str)
            to_send = 'K' + struct.pack("B", self.checksum('K'))
            self.ser.write(to_send)

        # pull these extra bytes out.  also not sure why...
        cam = self.ser.read(1)
        cam = self.ser.read(1)
        cam = self.ser.read(1)
        cam = self.ser.read(1)
        cam = self.ser.read(1)

        # this is ugly and there has to be a better way, but it works.
        earr = [z for z in imag_str[::2]]
        oarr = [z for z in imag_str[1::2]]
        arr = []

        for i in range(len(earr)):
            s = struct.pack("BB", earr[i], oarr[i])
            n = struct.unpack("H", s)[0]
            arr.append(n)
        
        if cropped:
            imag = np.array(arr, dtype=np.int32).reshape(480, 512)
        else:
            imag = np.array(arr, dtype=np.int32).reshape(480, 640)
        return np.flipud(imag)

if __name__ == '__main__':
    cam = AllSky340()
    print cam.firmware()
