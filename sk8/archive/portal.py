# webserver, human interface to monitor and emergency stop
# in browser, localhost:8080 or 127.0.0.1:8080

# http.server.HTTPServer is a socketserver.TCPServer subclass
# http.server.BaseHTTPRequestHandler, no handlers
# http.server.SimpleHTTPRequestHandler, includes do_GET and do_HEAD
# python -m http.server 8000 # start server with SimpleHTTPRequestHandler

import http.server
import os
import psutil
import threading
import monad

class Portal:
	PORT = 8080
	IP = ''
	server_address = (IP, PORT)

	def __init__(self):
		server = http.server.HTTPServer(self.server_address, self.AjaxServer)
		thread = threading.Thread(target = server.serve_forever)
		thread.daemon = True
		try:
			thread.start()
		except KeyboardInterrupt:
			server.shutdown()
			sys.exit(0)
		monad.log('portal server thread started')

	def processRequest(self,req,data):
		[path,svc] = os.path.split(req)
		code = 200
		out = ''
		if svc in ['start','stop','resume','home','kill']:
			monad.cortex.command(svc)
		elif svc == 'getwifi':
			out = monad.eyes.getConnection()
		elif svc == 'getstate':
			out = monad.eyes.getState() 
		else:
			code = 403
		return [code,out]
	
	class AjaxServer(http.server.SimpleHTTPRequestHandler):
		def do_GET(self):
			global shtml
			code = 200
			output = ''
			if self.path == '/favicon.ico':
				file_contents = open(self.path[1:], 'rb').read()
				output = bytes(file_contents)
			else:
				if self.path == '/':
					file_contents = shtml
				else:
					file_contents = "File not found"
					code = 404
				output = bytes(file_contents, 'utf-8')
	
			self.send_response(code)
			self.send_header("Content-type", "text/html")
			self.end_headers()
			self.flush_headers()
			self.wfile.write(output)
	
		def do_POST(self):
			length = int(self.headers.get_all('content-length')[0])
			req = self.path
			postin = self.rfile.read(length)
			postout = 'response to ajax call'
			[code,postout] = monad.portal.processRequest(req,postin)
			self.send_response(code)  # 200
			self.send_header("Content-type", "text/plain")
			self.end_headers()
			self.flush_headers()
			self.wfile.write(postout.encode())
	
shtml = '''
<!doctype html>
<html>
	<head>
		<meta http-equiv=Content-Type content='text/html; charset=UTF-8'>
		<meta name='viewport' content='width=device-width, initial-scale=1, maximum-scale=1'>
		<title>sk8 portal</title>
		<style>[hidden] {display:none ! important;}</style>
		<script type='text/javascript'>
			function xml_http_post(url, data, func) {
				var req = new XMLHttpRequest();
				req.open('POST', url, true);
				req.onreadystatechange = function() {
					if (req.readyState == 4) {
						if (func) {
							func(req.responseText);
						}
					}
				}
				req.send(data);
			}
			
			window.addEventListener('load', function() {
				var list = document.querySelectorAll('button');
				list.forEach(function(el) {
					el.addEventListener('click', function(e) {
						var action = e.currentTarget.id;
						xml_http_post('svc/'+action, action, false)
					});
				});
				getWifi();
				document.getElementById('getwifi').addEventListener('click', function(e) {
					getWifi();
				});
			});

			function getWifi() {
				xml_http_post('svc/getwifi', 'getwifi', function(response) {
					document.getElementById('wifi').innerHTML = response;
				})
			}

			function getState() {
			}
	</script>
	</head>	
	<body>
		<p>sk8 portal</p>
		<p>wifi: <span id='wifi'></span> <input type='button' id='getwifi' value='&#x21bb' /></p>
		<p>state: <span id='state'></span></p>
		<button id='start' >Start</button>
		<button id='stop'  >Stop</button>
		<button id='resume'>Resume</button>
		<button id='home'  >Home</button>
		<button id='kill'  >Kill</button>
		<div id='map'></div>
	</body>
</html>


<!--
once every second, 
	call for map data
	draw the map

mapdata = {
	state:'stopped',
	dronebattery:99,
	wheelbattery:87,
	judsonbattery:44,
	arduinobattery:63,
	altitude:800,
	h:300,
	w:600,
	wheels:{x:23,y:40},
	eyes:{x:150,y:300},
	origin:{x:0, y:6},
	cones: [
		{x:30,y:60},
		{x:30,y:60},
		{x:30,y:60}
	]
};
-->
'''
	
