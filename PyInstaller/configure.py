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

import sys
import time

from . import  compat
from . import log as logging
from .compat import is_win, is_darwin

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


def _get_pyinst_config_dir():
    if compat.getenv('PYINSTALLER_CONFIG_DIR'):
        config_dir = compat.getenv('PYINSTALLER_CONFIG_DIR')
    elif is_win:
        config_dir = compat.getenv('APPDATA')
        if not config_dir:
            config_dir = os.path.expanduser('~\\Application Data')
    elif is_darwin:
        config_dir = os.path.expanduser('~/Library/Application Support')
    else:
        # According to XDG specification
        # http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
        config_dir = compat.getenv('XDG_DATA_HOME')
        if not config_dir:
            config_dir = os.path.expanduser('~/.local/share')
    config_dir = os.path.join(config_dir, 'pyinstaller')
    return config_dir


def get_importhooks_dir(hook_type=None):
    from . import PACKAGEPATH
    if not hook_type:
        return os.path.join(PACKAGEPATH, 'hooks')
    else:
        return os.path.join(PACKAGEPATH, 'hooks', hook_type)


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
    config['configdir'] = _get_pyinst_config_dir()

    return config
