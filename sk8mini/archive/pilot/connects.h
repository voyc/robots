
'''
we could use the in-house local network, but the esp32-cam does not work in that config
also, we will not have that network available in the field 

so we let the awacs esp32 create a local network as a wifi access point
then both my laptop and the sk8mini connect as stations to that access point

awacs - running local network access point named awacs, also running webserver on 192.168.4.1
sk8mini - connects to awacs network, running webserver as 192.168.4.2  
racerswift:
  pilot.py connects to awacs network, http gets to sk8mini webserver 
  cam.py connects to awacs network, http gets to awacs webserver

awacs CameraWebServer.ino (example) creates network access point and starts a webserver
sk8mini.ino connects to awacs network and starts a webserver
pilot.py connects to awacs network and makes calls to the sk8mini webserver
cam.py connects to awacs network and makes "capture" gets to the awacs webserver
'''


camurl = 'http://192.168.4.1'   # when connected to access point AWACS
#camurl = 'http://192.168.1.102'  # when connected as station to JASMINE_2G, cam don't work
