import os
import sys

if sys.platform == 'darwin':
    d = os.path.join(sys._MEIPASS, 'QtWebEngineProcess.app', 'Contents', 'MacOS', 'QtWebEngineProcess')
    os.environ['QTWEBENGINEPROCESS_PATH'] = d
