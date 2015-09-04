import os
import sys

if sys.platform == 'darwin':  # TODO check if this is needed on linux
    os.environ['SSL_CERT_FILE'] = os.path.join(sys._MEIPASS, 'lib', 'cert.pem')
