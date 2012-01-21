#! /usr/bin/env python
#
# Configure PyInstaller for the current Python installation.
#
# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

import os
import sys
import shutil
import re
import time
import inspect

from PyInstaller import HOMEPATH, DEFAULT_CONFIGFILE, PLATFORM
from PyInstaller import is_win, is_unix, is_darwin, is_py24, get_version

import PyInstaller.mf as mf
import PyInstaller.build as build
import PyInstaller.compat as compat

import PyInstaller.log as logging
logger = logging.getLogger('PyInstaller.configure')


def find_EXE_dependencies(config):
    logger.info("Computing EXE_dependencies")
    python = sys.executable
    config['python'] = python
    config['target_platform'] = sys.platform


def test_Crypt(config):
    # TODO: disabled for now
    config["useCrypt"] = 0
    return

    #Crypt support. We need to build the AES module and we'll use distutils
    # for that. FIXME: the day we'll use distutils for everything this will be
    # a solved problem.
    logger.info("trying to build crypt support...")
    from distutils.core import run_setup
    cwd = os.getcwd()
    args = sys.argv[:]
    try:
        os.chdir(os.path.join(HOMEPATH, "source", "crypto"))
        dist = run_setup("setup.py", ["install"])
        if dist.have_run.get("install", 0):
            config["useCrypt"] = 1
            logger.info("... crypto support available")
        else:
            config["useCrypt"] = 0
            logger.info("... error building crypto support")
    finally:
        os.chdir(cwd)
        sys.argv = args


def test_Zlib(config):
    #useZLIB
    logger.info("testing for Zlib...")
    try:
        import zlib
        config['useZLIB'] = 1
        logger.info('... Zlib available')
    except ImportError:
        config['useZLIB'] = 0
        logger.info('... Zlib unavailable')


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

    test_exe = os.path.join(HOMEPATH, 'support', 'loader', PLATFORM, 'runw.exe')
    if not os.path.exists(test_exe):
        config['hasRsrcUpdate'] = 0
        logger.error('... resource update unavailable - %s not found', test_exe)
        return

    # The test_exe may be read-only
    # make a writable copy and test using that
    rw_test_exe = os.path.join(compat.getenv('TEMP'), 'me_test_exe.tmp')
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
    logger.info('testing for UPX...')
    cmd = "upx"
    if upx_dir:
        cmd = os.path.normpath(os.path.join(upx_dir, cmd))

    hasUPX = 0
    try:
        vers = compat.exec_command(cmd, '-V').strip().splitlines()
        if vers:
            v = vers[0].split()[1]
            hasUPX = tuple(map(int, v.split(".")))
            if is_win and is_py24 and hasUPX < (1, 92):
                logger.error('UPX is too old! Python 2.4 under Windows requires UPX 1.92+')
                hasUPX = 0
        logger.info('...UPX %s', ('unavailable', 'available')[hasUPX != 0])
    except Exception, e:
        logger.info('...exception result in testing for UPX')
        logger.info('  %r %r', e, e.args)
    config['hasUPX'] = hasUPX
    config['upx_dir'] = upx_dir


def find_PYZ_dependencies(config):
    logger.info("computing PYZ dependencies...")
    # We need to import `archive` from `PyInstaller` directory, but
    # not from package `PyInstaller`
    import PyInstaller.loader
    a = mf.ImportTracker([
        os.path.dirname(inspect.getsourcefile(PyInstaller.loader)),
        os.path.join(HOMEPATH, 'support')])

    a.analyze_r('archive')
    mod = a.modules['archive']
    toc = build.TOC([(mod.__name__, mod.__file__, 'PYMODULE')])
    for i, (nm, fnm, typ) in enumerate(toc):
        mod = a.modules[nm]
        tmp = []
        for importednm, isdelayed, isconditional, level in mod.imports:
            if not isconditional:
                realnms = a.analyze_one(importednm, nm)
                for realnm in realnms:
                    imported = a.modules[realnm]
                    if not isinstance(imported, mf.BuiltinModule):
                        tmp.append((imported.__name__, imported.__file__, imported.typ))
        toc.extend(tmp)
    toc.reverse()
    config['PYZ_dependencies'] = toc.data


def __add_options(parser):
    """
    Add the `Configure` options to a option-parser instance or a
    option group.
    """
    parser.add_option('--upx-dir', default=None,
                      help='Directory containing UPX.')
    parser.add_option('-C', '--configfile',
                      default=DEFAULT_CONFIGFILE,
                      dest='configfilename',
                      help='Name of generated configfile (default: %default)')


def main(configfilename, upx_dir, **kw):

    if is_darwin and compat.architecture() == '64bit':
        logger.warn('You are running 64-bit Python. Created binary will not'
            ' work on Mac OS X 10.4 or 10.5. For this version it is necessary'
            ' to create 32-bit binaries.'
            ' If you need 32-bit version of Python, run Python as 32-bit binary'
            ' by command:\n\n'
            '    arch -i386 python\n')
        # wait several seconds for user to see this message
        time.sleep(4)

    try:
        config = build._load_data(configfilename)
        logger.info('read old config from %s', configfilename)
    except (IOError, SyntaxError):
        # IOerror: file not present/readable
        # SyntaxError: invalid file (platform change?)
        # if not set by Make.py we can assume Windows
        config = {'useELFEXE': 1}

    # Save Python version, to detect and avoid conflicts
    config["pythonVersion"] = sys.version
    config["pythonDebug"] = __debug__

    # Save PyInstaller path and version
    config["pyinstaller_version"] = get_version()
    config["pyinstaller_homepath"] = HOMEPATH

    find_EXE_dependencies(config)
    test_Zlib(config)
    test_Crypt(config)
    test_RsrcUpdate(config)
    test_UPX(config, upx_dir)
    find_PYZ_dependencies(config)

    build._save_data(configfilename, config)
    logger.info("done generating %s", configfilename)
