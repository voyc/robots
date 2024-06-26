
import subprocess
import nmcli


#nmcli device wifi connect AWACS password indecent

#rc = subprocess.run(['nmcli', 'device', 'wifi', 'connect', 'AWACS', 'password', 'indecent'])
#print(rc)


def netup(ssid, pw):
	print('connect wifi')
	nmcli.disable_use_sudo()
	nmcli.device.wifi_connect(ssid, pw)
	print('wifi connected')

try:
	#nmcli.device.wifi_connect('AWACS', 'indecent')
	netup('AWACS', 'indecent')
except Exception as ex:
	print(f'awacs not connected')

'''
the nmcli command writes to stdout
the subprocess.run(nmcli) does not return a value, and does not raise and exception
so there is no way to know whether it worked or not
'''


