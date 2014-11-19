#!/bin/sh

cd /Library/WebServer/Documents
rsync -a -e ssh massdimm@massdimm:/var/www/skycam .
sleep 20
rsync -a -e ssh massdimm@massdimm:/var/www/skycam .
