#!/usr/bin/env python3
"""
NAI Batch Runner local proxy.

- Serves files from this directory on http://localhost:8787/
- Proxies /user/*  -> https://api.novelai.net
- Proxies /ai/*    -> https://image.novelai.net
- Adds permissive CORS headers so the browser is happy.

When run via `pythonw.exe` (no console), all stdout/stderr is captured
in `proxy.log` next to this file. A `.proxy.pid` file is written for
stop.bat to find the right process.

Usage:
    python proxy.py        # foreground with console (debug)
    pythonw proxy.py       # background, silent (run.bat does this)
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(ROOT, 'proxy.log')
PID_FILE = os.path.join(ROOT, '.proxy.pid')

# Rotate log if it gets large (single rotation, .old)
try:
    if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 5 * 1024 * 1024:
        os.replace(LOG_PATH, LOG_PATH + '.old')
except Exception:
    pass

# Redirect stdout/stderr to log file so pythonw.exe (no console) still records output.
# Only redirect when not attached to a console — i.e. when running under pythonw.
try:
    _log = open(LOG_PATH, 'a', encoding='utf-8', buffering=1)
    sys.stdout = _log
    sys.stderr = _log
except Exception:
    pass

import http.server
import socketserver
import urllib.request
import urllib.error
import threading
import webbrowser
import socket
import atexit
import datetime

PORT = 8787

ROUTES = [
    ('/user/', 'https://api.novelai.net'),
    ('/ai/',   'https://image.novelai.net'),
]

FORWARD_REQ_HEADERS = ('Authorization', 'Content-Type', 'Accept', 'User-Agent')
DEFAULT_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
              'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')


def _ts():
    return datetime.datetime.now().strftime('%H:%M:%S')


def _log(msg):
    sys.stderr.write(f'[{_ts()}] {msg}\n')


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
        _log(f'-> {method} {url}')

        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                _log(f'<- {resp.status} {url}')
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
            _log(f'<- {e.code} {url} ({len(data)}B)')
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
        _log("%s - %s" % (self.address_string(), fmt % args))


class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def _is_port_in_use(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', port)) == 0
    except Exception:
        return False


def _write_pid():
    try:
        with open(PID_FILE, 'w', encoding='utf-8') as f:
            f.write(str(os.getpid()))
    except Exception:
        pass


def _cleanup_pid():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r', encoding='utf-8') as f:
                pid = f.read().strip()
            # only delete if this process owns it (best-effort)
            if pid == str(os.getpid()):
                os.remove(PID_FILE)
    except Exception:
        pass


atexit.register(_cleanup_pid)


if __name__ == '__main__':
    _log('=' * 60)
    _log(f'proxy.py starting (pid={os.getpid()})')

    url = f'http://localhost:{PORT}/index.html'

    # If already running, just open the browser to it and exit.
    if _is_port_in_use(PORT):
        _log(f'Port {PORT} already in use — opening browser to existing instance.')
        try:
            webbrowser.open(url)
        except Exception as e:
            _log(f'webbrowser.open failed: {e}')
        sys.exit(0)

    _write_pid()

    try:
        with ThreadingServer(('127.0.0.1', PORT), Handler) as httpd:
            _log(f'Serving  http://localhost:{PORT}/')
            _log(f'  static : {ROOT}')
            _log(f'  /user/* -> api.novelai.net')
            _log(f'  /ai/*   -> image.novelai.net')
            _log(f'Opening {url} ...')
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                _log('KeyboardInterrupt — shutting down.')
    except OSError as e:
        _log(f'Failed to bind to port {PORT}: {e}')
        sys.exit(1)
    except Exception as e:
        _log(f'Fatal: {e}')
        sys.exit(1)
