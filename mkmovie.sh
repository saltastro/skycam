#!/bin/bash

skycamdatadir=/var/www/skycam/$(date +%Y/%m%d)

x=1
for i in `ls $skycamdatadir/*.jpg | tail -200`;
	do counter=$(printf %03d $x);
	ln -sf "$i" /tmp/img"$counter".jpeg;
	x=$(($x+1));
done

/usr/bin/avconv -y -r 10 -q:v 0 -f image2 -i /tmp/img%03d.jpeg /tmp/latest_anim.mp4
/usr/bin/avconv -i /tmp/latest_anim.mp4 -y -minrate 2M -maxrate 2M -b:v 2M /tmp/latest_anim.webm

rsync --copy-links -a /tmp/latest_anim.webm web.saao.ac.za::skycam/anim/

rm -fr /tmp/latest_anim.mp4
rm -fr /tmp/latest_anim.webm
rm -fr /tmp/img*.jpeg
