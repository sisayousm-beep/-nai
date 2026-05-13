#!/usr/bin/env python3
"""
NAI Batch Runner local proxy.

- Serves files from this directory on http://localhost:8787/
- Proxies /user/*  -> https://api.novelai.net
- Proxies /ai/*    -> https://image.novelai.net
- Adds permissive CORS headers so the browser is happy.

Usage:
    python proxy.py
    # then open http://localhost:8787/index.html
    # and set "API Base URL" in 설정 to: http://localhost:8787
"""
import http.server
import socketserver
import urllib.request
import urllib.error
import os
import sys
import threading
import webbrowser

PORT = 8787
ROOT = os.path.dirname(os.path.abspath(__file__))

ROUTES = [
    ('/user/', 'https://api.novelai.net'),
    ('/ai/',   'https://image.novelai.net'),
]

FORWARD_REQ_HEADERS = ('Authorization', 'Content-Type', 'Accept', 'User-Agent')
DEFAULT_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
              'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type, Accept')
        self.send_header('Access-Control-Max-Age', '86400')

    def _match_route(self):
        for prefix, target in ROUTES:
            if self.path.startswith(prefix):
                return target + self.path
        return None

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _proxy(self, method):
        url = self._match_route()
        if not url:
            if method == 'GET':
                return super().do_GET()
            self.send_error(404, 'No proxy route')
            return

        length = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(length) if length else None

        req = urllib.request.Request(url, data=body, method=method)
        for h in FORWARD_REQ_HEADERS:
            v = self.headers.get(h)
            if v:
                req.add_header(h, v)
        if not req.has_header('User-agent'):
            req.add_header('User-Agent', DEFAULT_UA)
        sys.stderr.write(f'[proxy] -> {method} {url}\n')

        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                sys.stderr.write(f'[proxy] <- {resp.status} {url}\n')
                self.send_response(resp.status)
                ctype = resp.headers.get('Content-Type')
                clen = resp.headers.get('Content-Length')
                if ctype:
                    self.send_header('Content-Type', ctype)
                if clen:
                    self.send_header('Content-Length', clen)
                self._cors()
                self.end_headers()
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except urllib.error.HTTPError as e:
            data = e.read()
            sys.stderr.write(f'[proxy] <- {e.code} {url} ({len(data)}B)\n')
            self.send_response(e.code)
            ctype = e.headers.get('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self._cors()
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            msg = f'Proxy error: {e}'.encode('utf-8')
            self.send_response(502)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(msg)))
            self._cors()
            self.end_headers()
            self.wfile.write(msg)

    def do_GET(self):
        if self._match_route():
            self._proxy('GET')
        else:
            super().do_GET()

    def do_POST(self):
        self._proxy('POST')

    def log_message(self, fmt, *args):
        sys.stderr.write("[proxy] %s - %s\n" % (self.address_string(), fmt % args))


class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == '__main__':
    with ThreadingServer(('127.0.0.1', PORT), Handler) as httpd:
        print(f'Serving  http://localhost:{PORT}/')
        print(f'  static : {ROOT}')
        print(f'  /user/* -> api.novelai.net')
        print(f'  /ai/*   -> image.novelai.net')
        url = f'http://localhost:{PORT}/index.html'
        print(f'Opening {url} ...')
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nBye.')
