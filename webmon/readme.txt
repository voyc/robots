
difference between starting locally in the background and at boot?

Copy the shell command to /usr/bin/ and make it executable.
$ sudo cp webmon.sh /usr/bin/
$ sudo chmod +x /usr/bin/webmon.sh

Copy the service file to /etc/systemd/system/ and set permissions.
$ sudo cp webmon.service /etc/systemd/system/
$ sudo chmod 644 /etc/systemd/system/webmon.service

Run the service.
$ sudo systemctl start webmon
$ sudo systemctl status webmon
$ sudo systemctl stop webmon
$ sudo systemctl enable webmon  # service will start at boot  

