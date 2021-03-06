#!/usr/bin/env python

import os
import datetime as dt
import time

from astropy.io import fits as pyfits
import matplotlib
matplotlib.use('Agg')
import pylab as pl
import numpy as np
from scipy import stats
from AllSky340 import AllSky340

cam = AllSky340(port="/dev/ttyUSB0",
                baudrate=460800,
                timeout=0.1)
cam.log_info("Image acquisition script starting up.")

ndark = 0
exp = 60.0

os.chdir("/var/www/skycam/")

def get_obsdir():
   """return the obsdate directory"""
   now = dt.datetime.now() - dt.timedelta(days=0.5)
   year = now.strftime('%Y/')
   obsdir=now.strftime('%Y/%m%d/')
   if not os.path.isdir(year): os.mkdir(year)
   if not os.path.isdir(obsdir): os.mkdir(obsdir)
   return obsdir
    

while True:
    if os.path.isfile("STOP"):
        cam.log_info("Image acquisition script shutting down.")
        os.system("rm STOP")
        break

    try:
        if ndark == 0:
            dark = cam.getImage(exp, light=False)
            ndark += 1

        imag = cam.getImage(exp, light=True)

        # get the time and set up labels and filenames
        obsdir = get_obsdir()
        now = time.localtime()
        imag -= dark
        min = stats.scoreatpercentile(imag.flat, 1)
        max = stats.scoreatpercentile(imag.flat, 99.5)
        filename = obsdir+time.strftime("AllSky_%Y%m%d_%H%M%S.fits")
        jpg = obsdir+time.strftime("AllSky_%Y%m%d_%H%M%S.jpg")
        date = time.strftime("%Y/%m/%d")
        sast = time.strftime("%H:%M:%S")
        elabel = "Exposure: %f sec" % exp

        # set up and create the FITS file
        cards = []
        cards.append(pyfits.createCard("DATEOBS", date, "Date of observation"))
        cards.append(pyfits.createCard("TIMEOBS",
                                       sast,
                                       "Time of observation (SAST)"))
        cards.append(pyfits.createCard("EXPTIME", exp, "Exposure time (s)"))
        header = pyfits.Header(cards=cards)
        pyfits.writeto(filename, imag, header=header, clobber=True)

        # set up and create the JPG file
        fig = pl.figure()
        ax = fig.add_subplot(111)
        ax.set_axis_off()
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.set_xticks([])
        ax.set_yticks([])
        pl.imshow(np.flipud(imag), cmap=matplotlib.cm.gray, aspect='normal',
            vmin=min, vmax=max)
        pl.text(10, 5, date, color='w',
            verticalalignment='top', fontweight='bold')
        pl.text(630, 5, sast, color='w',
            verticalalignment='top', horizontalalignment='right',
            fontweight='bold')
        pl.text(10, 475, "%.2g sec" % exp, color='w', fontweight='bold')
        pl.savefig(jpg, bbox_inches="tight", pad_inches=0.0, quality=95)
        pl.close()

        os.system("ln -sf /var/www/skycam/%s Data/AllSkyCurrentImage.JPG" % jpg)
        os.system("ln -sf /var/www/skycam/%s Data/AllSkyCurrentImage.fits" % filename)

    except Exception, err:
        cam.log_err("Oops! Something went wrong...%s" % err) 

    ndark += 1

    if ndark > 10:
        ndark = 0

    if np.median(imag) > 15000.0:
        exp /= 2.0
        ndark = 0

    if np.median(imag) < 4000.0 and exp < 60.0:
        exp *= 2.0
        ndark = 0
