#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Configure PyInstaller for the current Python installation.
"""

import os
import shutil
import sys
import tempfile
import time

from PyInstaller import HOMEPATH, PLATFORM
from PyInstaller.compat import is_win, is_darwin

import PyInstaller.compat as compat
from PyInstaller.depend.analysis import TOC

import PyInstaller.log as logging

logger = logging.getLogger(__name__)


def test_UPX(config, upx_dir):
    logger.debug('Testing for UPX ...')
    cmd = "upx"
    if upx_dir:
        cmd = os.path.normpath(os.path.join(upx_dir, cmd))

    hasUPX = 0
    try:
        vers = compat.exec_command(cmd, '-V').strip().splitlines()
        if vers:
            v = vers[0].split()[1]
            hasUPX = tuple(map(int, v.split(".")))
            if is_win and hasUPX < (1, 92):
                logger.error('UPX is too old! Python 2.4 under Windows requires UPX 1.92+')
                hasUPX = 0
    except Exception as e:
        if isinstance(e, OSError) and e.errno == 2:
            # No such file or directory
            pass
        else:
            logger.info('An exception occured when testing for UPX:')
            logger.info('  %r', e)
    if hasUPX:
        is_available = 'available'
    else:
        is_available = 'not available'
    logger.info('UPX is %s.', is_available)
    config['hasUPX'] = hasUPX
    config['upx_dir'] = upx_dir


def get_config(upx_dir, **kw):
    if is_darwin and compat.architecture() == '64bit':
        logger.warn('You are running 64-bit Python: created binaries will only'
            ' work on Mac OS X 10.6+.\nIf you need 10.4-10.5 compatibility,'
            ' run Python as a 32-bit binary with this command:\n\n'
            '    VERSIONER_PYTHON_PREFER_32_BIT=yes arch -i386 %s\n' % sys.executable)
        # wait several seconds for user to see this message
        time.sleep(1)

    config = {}
    test_UPX(config, upx_dir)

    return config
