#!/usr/bin/env python

import time
import pyfits
from AllSky340 import AllSky340

cam = AllSky340(port="/dev/tty.usbserial-A700dzlT", baudrate=460800, timeout=1)
cam.log_info("Testing camera communication.")

p = cam.ping()
if p:
    exp = 0.1
    cam.log_info("Taking %f sec test image." % exp)
    imag = cam.getImage(exp, light=True)
    now = time.localtime()
    date = time.strftime("%Y/%m/%d")
    sast = time.strftime("%H:%M:%S")

    # set up and create the FITS file
    cards = []
    cards.append(pyfits.createCard("DATEOBS", date, "Date of observation"))
    cards.append(pyfits.createCard("TIMEOBS",
                                   sast,
                                   "Time of observation (SAST)"))
    cards.append(pyfits.createCard("EXPTIME", exp, "Exposure time (s)"))
    header = pyfits.Header(cards=cards)
    pyfits.writeto("test.fits", imag, header=header, clobber=True)

