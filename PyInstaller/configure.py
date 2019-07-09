#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
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

from . import compat
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
        vers = compat.exec_command(
            cmd, '-V', __raise_ENOENT__=True).strip().splitlines()
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


def _get_pyinst_cache_dir():
    old_cache_dir = None
    if compat.getenv('PYINSTALLER_CONFIG_DIR'):
        cache_dir = compat.getenv('PYINSTALLER_CONFIG_DIR')
    elif is_win:
        cache_dir = compat.getenv('APPDATA')
        if not cache_dir:
            cache_dir = os.path.expanduser('~\\Application Data')
    elif is_darwin:
        cache_dir = os.path.expanduser('~/Library/Application Support')
    else:
        # According to XDG specification
        # http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
        old_cache_dir = compat.getenv('XDG_DATA_HOME')
        if not old_cache_dir:
            old_cache_dir = os.path.expanduser('~/.local/share')
        cache_dir = compat.getenv('XDG_CACHE_HOME')
        if not cache_dir:
            cache_dir = os.path.expanduser('~/.cache')
    cache_dir = os.path.join(cache_dir, 'pyinstaller')
    # Move old cache-dir, if any, to now location
    if old_cache_dir and not os.path.exists(cache_dir):
        old_cache_dir = os.path.join(old_cache_dir, 'pyinstaller')
        if os.path.exists(old_cache_dir):
            parent_dir = os.path.dirname(cache_dir)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            os.rename(old_cache_dir, cache_dir)
    return cache_dir


#FIXME: Rename to get_official_hooks_dir().
#FIXME: Remove the "hook_type" parameter after unifying hook types.
def get_importhooks_dir(hook_type=None):
    from . import PACKAGEPATH
    if not hook_type:
        return os.path.join(PACKAGEPATH, 'hooks')
    else:
        return os.path.join(PACKAGEPATH, 'hooks', hook_type)


def get_config(upx_dir, **kw):
    config = {}
    test_UPX(config, upx_dir)
    config['cachedir'] = _get_pyinst_cache_dir()

    return config
