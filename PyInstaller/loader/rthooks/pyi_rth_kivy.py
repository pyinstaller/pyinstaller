import os
import sys

root = os.path.join(sys._MEIPASS, 'kivy_install')

os.environ['KIVY_DATA_DIR'] = os.path.join(root, 'data')
os.environ['KIVY_MODULES_DIR'] = os.path.join(root, 'modules')
