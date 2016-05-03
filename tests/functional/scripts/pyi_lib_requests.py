# -----------------------------------------------------------------------------
# Copyright (c) 2014-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------
import socket

try:
    import BaseHTTPServer
    import SimpleHTTPServer
except ImportError:
    import http.server as BaseHTTPServer
    import http.server as SimpleHTTPServer

import os
import ssl
import sys
import threading
import time

import requests

"""
Note: to re-create the server.pem file use the
following commands.

cd /path/to/pyinstaller.git/tests/functional
openssl req -new -x509 -keyout data/requests/server.pem \
    -text -out data/requests/server.pem -days 36500 \
    -nodes -config data/requests/openssl.conf
"""

if getattr(sys, 'frozen', False):
    # we are running in a |PyInstaller| bundle
    basedir = sys._MEIPASS
else:
    # we are running in a normal Python environment
    basedir = os.path.dirname(__file__)


SERVER_CERT = os.path.join(basedir, u"server.pem")


if not os.path.exists(SERVER_CERT):
    raise SystemExit('Certificate-File %s is missing' % SERVER_CERT)


def main():

    SERVER_PORT = 8443
    httpd = None

    # Since unit tests run in parallel, the port may be in use, so
    # retry creating the server while incrementing the port number
    while SERVER_PORT < 8493:  # Max 50 retries
        try:
            # SSL server copied from here:
            # http://www.piware.de/2011/01/creating-an-https-server-in-python/
            httpd = BaseHTTPServer.HTTPServer(
                ('localhost', SERVER_PORT),
                SimpleHTTPServer.SimpleHTTPRequestHandler)
        except socket.error as e:
            if e.errno == 98:  # Address in use
                SERVER_PORT += 1
                continue
            else:
                # Some other socket.error
                raise
        else:
            # Success
            break
    else:
        # Did not break from loop, so we ran out of retries
        assert False, "Could not bind server port: all ports in use."

    httpd.socket = ssl.wrap_socket(
        httpd.socket, certfile=SERVER_CERT, server_side=True,
        ssl_version=ssl.PROTOCOL_TLSv1,
    )

    def ssl_server():
        httpd.serve_forever()

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
