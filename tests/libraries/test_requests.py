# -----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------

import BaseHTTPServer
import SimpleHTTPServer

import os
import ssl
import sys
import threading
import time

import requests

"""
Note: to re-create the test_requests_server.pem file use the
following commands.

cd /path/to/pyinstaller.git/tests/libraries
openssl req -new -x509 -keyout test_requests_server.pem \
    -out test_requests_server.pem -days 365 \
    -nodes -config test_requests_openssl.conf
"""


SERVER_PORT = 8443
SERVER_CERT = os.path.join(
    os.path.dirname(sys.executable),
    u"test_requests_server.pem")


def ssl_server():
    # SSL server copied from here:
    # http://www.piware.de/2011/01/creating-an-https-server-in-python/
    httpd = BaseHTTPServer.HTTPServer(
        ('localhost', SERVER_PORT),
        SimpleHTTPServer.SimpleHTTPRequestHandler)
    httpd.socket = ssl.wrap_socket(
        httpd.socket, certfile=SERVER_CERT, server_side=True)
    httpd.serve_forever()


def main():
    # Start the SSL server
    thread = threading.Thread(target=ssl_server)
    thread.daemon = True
    thread.start()

    # Wait a bit for the server to start
    time.sleep(1)

    # Use requests to get a page from the server
    requests.get(
        u"https://localhost:{}".format(SERVER_PORT),
        verify=SERVER_CERT)
    # requests.get("https://github.com")

if __name__ == '__main__':
    main()
