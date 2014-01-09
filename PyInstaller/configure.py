#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Configure PyInstaller for the current Python installation.
"""


import inspect
import os
import shutil
import sys
import tempfile
import time

from PyInstaller import HOMEPATH, PLATFORM
from PyInstaller.compat import is_win, is_darwin

import PyInstaller.build as build
import PyInstaller.compat as compat

import PyInstaller.log as logging
import PyInstaller.depend.modules
import PyInstaller.depend.imptracker

logger = logging.getLogger(__name__)


def test_RsrcUpdate(config):
    config['hasRsrcUpdate'] = 0
    if not is_win:
        return
    # only available on windows
    logger.info("Testing for ability to set icons, version resources...")
    try:
        import win32api
        from PyInstaller.utils import icon, versioninfo
    except ImportError, detail:
        logger.info('... resource update unavailable - %s', detail)
        return

    test_exe = os.path.join(HOMEPATH, 'PyInstaller', 'bootloader', PLATFORM, 'runw.exe')
    if not os.path.exists(test_exe):
        config['hasRsrcUpdate'] = 0
        logger.error('... resource update unavailable - %s not found', test_exe)
        return

    # The test_exe may be read-only
    # make a writable copy and test using that
    rw_test_exe = os.path.join(tempfile.gettempdir(), 'me_test_exe.tmp')
    shutil.copyfile(test_exe, rw_test_exe)
    try:
        hexe = win32api.BeginUpdateResource(rw_test_exe, 0)
    except:
        logger.info('... resource update unavailable - win32api.BeginUpdateResource failed')
    else:
        win32api.EndUpdateResource(hexe, 1)
        config['hasRsrcUpdate'] = 1
        logger.info('... resource update available')
    os.remove(rw_test_exe)


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
    except Exception, e:
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


# TODO Drop this function when new module system based on 'modulegraph'
#      is in place.
def find_PYZ_dependencies(config):
    logger.debug("Computing PYZ dependencies")
    # We need to import `pyi_importers` from `PyInstaller` directory, but
    # not from package `PyInstaller`
    import PyInstaller.loader
    a = PyInstaller.depend.imptracker.ImportTracker([
        os.path.dirname(inspect.getsourcefile(PyInstaller.loader)),
        os.path.join(HOMEPATH, 'support')])

    # Frozen executable needs some modules bundled as bytecode objects ('PYMODULE' type)
    # for the bootstrap process. The following lines ensures that.
    # It's like making those modules 'built-in'.
    # 'pyi_importers' is the base module that should be available as bytecode (co) object.
    a.analyze_r('pyi_importers')
    mod = a.modules['pyi_importers']
    toc = build.TOC([(mod.__name__, mod.__file__, 'PYMODULE')])
    for i, (nm, fnm, typ) in enumerate(toc):
        mod = a.modules[nm]
        tmp = []
        for importednm, isdelayed, isconditional, level in mod.pyinstaller_imports:
            if not isconditional:
                realnms = a.analyze_one(importednm, nm)
                for realnm in realnms:
                    imported = a.modules[realnm]
                    if not isinstance(imported, PyInstaller.depend.modules.BuiltinModule):
                        tmp.append((imported.__name__, imported.__file__, imported.typ))
        toc.extend(tmp)
    toc.reverse()
    config['PYZ_dependencies'] = toc.data


def get_config(upx_dir, **kw):
    if is_darwin and compat.architecture() == '64bit':
        logger.warn('You are running 64-bit Python: created binaries will only'
            ' work on Mac OS X 10.6+.\nIf you need 10.4-10.5 compatibility,'
            ' run Python as a 32-bit binary with this command:\n\n'
            '    VERSIONER_PYTHON_PREFER_32_BIT=yes arch -i386 %s\n' % sys.executable)
        # wait several seconds for user to see this message
        time.sleep(4)

    config = {}
    test_RsrcUpdate(config)
    test_UPX(config, upx_dir)
    find_PYZ_dependencies(config)
    return config
