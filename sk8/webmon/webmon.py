import http.server
import os
import psutil

PORT = 8080
IP = ''
server_address = (IP, PORT)

# http.server.HTTPServer is a socketserver.TCPServer subclass
# http.server.BaseHTTPRequestHandler, no handlers
# http.server.SimpleHTTPRequestHandler, includes do_GET and do_HEAD
# python -m http.server 8000 # start server with SimpleHTTPRequestHandler

def processRequest(req,data):
	global gstate
	[path,svc] = os.path.split(req)
	code = 200
	out = ''
	if svc == 'go':
		gstate = 'started'
		out = gstate
	elif svc == 'stop':
		gstate = 'stopped'
		out = gstate
	elif svc == 'emer':
		gstate = 'emergency'
		out = gstate
	elif svc == 'getmap':
		out = 'mapdata '
		#out += getBattery()
	else:
		code = 403
	return [code,out]

def getBattery():
	battery = psutil.sensors_battery()  # returns null
	plugged = battery.power_plugged
	percent = str(battery.percent) 
	plugged = "Plugged In" if plugged else "Not Plugged In"
	return str(battery.percent)+'%, '+plugged

class AjaxServer(http.server.SimpleHTTPRequestHandler):

	def do_GET(self):
		filename = 'index.html'
		if self.path == '/':
			try:
				#file_contents = open(self.path[1:]).read()
				file_contents = open(filename).read()
				self.send_response(200)
			except:
				file_contents = "File not found"
				self.send_response(404)
		else:
			file_contents = "File not found"
			self.send_response(403)

		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.flush_headers()
		self.wfile.write(bytes(file_contents, 'utf-8'))

	def do_POST(self):
		#print(self.headers)
		length = int(self.headers.get_all('content-length')[0])
		req = self.path
		postin = self.rfile.read(length)
		postout = 'response to ajax call'
		[code,postout] = processRequest(req,postin)
		#self.log_message(f'req:{req}, in:{postin}, out:{postout}')  # to stderr
		#msg = f'req:{req}, in:{postin}, out:{postout}'
		self.send_response(code)  # 200
		self.send_header("Content-type", "text/plain")
		self.end_headers()
		self.flush_headers()
		self.wfile.write(postout.encode())

server = http.server.HTTPServer(server_address, AjaxServer)
server.serve_forever()
server_message('starting')
