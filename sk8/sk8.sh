#!/bin/bash

# Copy the shell command to /usr/bin/ and make it executable.
# $ sudo cp sk8.sh /usr/bin/
# $ sudo chmod +x /usr/bin/sk8.sh
# 
# Copy the service file to /etc/systemd/system/ and set permissions.
# $ sudo cp sk8.service /etc/systemd/system/
# $ sudo chmod 644 /etc/systemd/system/sk8.service
# 
# Run the service.
# $ sudo systemctl start sk8
# $ sudo systemctl status sk8
# $ sudo systemctl stop sk8
# $ sudo systemctl enable sk8  # service will start at boot  

cd /home/john/webapps/robots/robots/sk8/ 
python3 -u sk8.py &>> /var/log/sk8.log
