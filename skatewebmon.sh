#!/bin/bash
python3 -u webmon.py &>> /var/log/skate/webmon.log & 
echo $! >> /var/log/skate/webmon.log
