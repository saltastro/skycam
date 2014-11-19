#!/usr/bin/env python

from AllSky340 import AllSky340

#cam = AllSky340(port="/dev/tty.usbserial-A700dzlT", baudrate=460800, timeout=1)
cam = AllSky340(port="/dev/ttyUSB1", baudrate=460800, timeout=1)
cam.log_info("Testing camera communication.")

p = cam.ping()
if p:
    cam.firmware()
