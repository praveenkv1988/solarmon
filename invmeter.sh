#!/bin/sh
while [ 1 ]
do
    /var/solarmon/inv_read.py
    sleep 10
done
