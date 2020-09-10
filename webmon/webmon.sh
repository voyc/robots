#!/bin/bash
cd /home/john/webapps/robots/robots/webmon/ 
python3 -u webmon.py &>> /var/log/skate/webmon.log
