import glob
import os
import sys

import PyInstaller.log as logging
from PyInstaller.compat import is_darwin, is_win
from PyInstaller.utils.hooks import get_typelibs, exec_statement

logger = logging.getLogger(__name__)


hiddenimports = ['gi.overrides.Gio']


datas = get_typelibs('Gio', '2.0')


binaries = []

statement = """
from gi.repository import Gio
print(Gio.__path__)
"""

path = exec_statement(statement)
pattern = None

if is_darwin:
    pattern = os.path.join(os.path.commonprefix([sys.prefix, path]), 'lib', 'gio', 'modules', '*.so')
elif is_win:
    pattern = os.path.join(os.path.dirname(path), '..', 'gio', 'modules', '*.dll')

if pattern:
    for f in glob.glob(pattern):
        binaries.append((f, 'gio_modules'))
else:
    logger.warn('Bundling Gio modules is currently not supported on your platform.')
