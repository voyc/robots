import http.server
import os

PORT = 8080
IP = ''
server_address = (IP, PORT)

# http.server.HTTPServer is a socketserver.TCPServer subclass
# http.server.BaseHTTPRequestHandler, no handlers
# http.server.SimpleHTTPRequestHandler, includes do_GET and do_HEAD
# python -m http.server 8000 # start server with SimpleHTTPRequestHandler

def processRequest(req,data):
    [head,tail] = os.path.split(req)
    print(head)
    print(tail)
    return 'ok'

def doStart():
    return 'ok'

def doStop():
    return 'ok'

def doEmer():
    return 'ok'

def doGetData():
    judsonbattery: random(1,100)
    return 'ok'

class AjaxServer(http.server.SimpleHTTPRequestHandler):

    #def do_GET(self):
    #    if self.path == '/':
    #        self.path = '/index.html'
    #    try:
    #        file_contents = open(self.path[1:]).read()
    #        self.send_response(200)
    #    except:
    #        file_contents = "File not found"
    #        self.send_response(404)
    #    self.send_header("Content-type", "text/html")
    #    self.end_headers()
    #    self.flush_headers()
    #    self.wfile.write(bytes(file_contents, 'utf-8'))

    def do_POST(self):
        #print(self.headers)
        length = int(self.headers.get_all('content-length')[0])
        req = self.path
        postin = self.rfile.read(length)
        postout = 'response to ajax call'
        postout = processRequest(req,postin)
        self.send_response(200)
        self.log_message(f'req:{req}, in:{postin}, out:{postout}')
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.flush_headers()
        self.wfile.write(postout.encode())

print('Serving HTTP...')
server = http.server.HTTPServer(server_address, AjaxServer)
server.serve_forever()
