"""
    speed_pefile
"""
import os
import shutil
from PyInstaller import log
from PyInstaller.building.build_main import Analysis
from PyInstaller.config import CONF

import time

from os.path import join
from tempfile import mkdtemp
logger = log.getLogger(__name__)


def speed_pefile():
    log.logging.basicConfig(level=log.DEBUG)

    tempdir = mkdtemp("speed_pefile")
    workdir = join(tempdir, "build")
    distdir = join(tempdir, "dist")
    script = join(tempdir, 'speed_pefile_script.py')
    warnfile = join(workdir, 'warn.txt')
    os.makedirs(workdir)
    os.makedirs(distdir)

    with open(script, 'w') as f:
        f.write('''
from PySide import QtCore
from PySide import QtGui
''')

    CONF['workpath'] = workdir
    CONF['distpath'] = distdir
    CONF['warnfile'] = warnfile
    CONF['hiddenimports'] = []
    CONF['spec'] = join(tempdir, 'speed_pefile_script.spec')

    CONF['specpath'] = tempdir
    CONF['specnm'] = 'speed_pefile_script'

    start = time.time()
    a = Analysis([script])
    duration = time.time() - start

    logger.warn("Analysis duration: %s", duration)
    shutil.rmtree(tempdir, ignore_errors=True)

if __name__ == '__main__':
    speed_pefile()