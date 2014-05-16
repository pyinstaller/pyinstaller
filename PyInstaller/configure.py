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


def test_RsrcUpdate(config):
    config['hasRsrcUpdate'] = 0
    if not is_win:
        return
    # only available on windows
    logger.info("Testing for ability to set icons, version resources...")
    try:
        import win32api
        from PyInstaller.utils.win32 import icon, versioninfo
    except ImportError as detail:
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
        # TODO use CopyIcons() from utils.win32.icon.py.
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


# TODO this temporary function returns a hard-coded list of modules.
# In future when Modulegraph retains the info to distinguish top-level
# imports from conditional and deferred imports, it can be recoded
# approximately as follows:
'''
    def node_name(node) :
        # Get a unique module name from a graph node including the 
        # case of a Script node where the identifier is a full path string
        ntype = type(node).__name__
        if ntype == 'Script' :
            return os.path.basename(node.filename)
        return node.identifier
    
    # Create a fresh graph initialized with pyi_importers.py
    mg = PyiModuleGraph(sys.path + ['path-to-PyInstaller/loader'])
    script_node = mg.run_script('full-path-to-pyi_importers.py'))
    # Extract from the graph the list of top-level non-conditional imports
    toc = TOC( [ (node_name(script_node), script_node.filename, 'PYMODULE') ] )
    node_list = [script_node]
    for i, importer in enumerate(node_list) :
        # Look at the edges emerging from that node:
        iter_out, _ = mg.get_edges(importer)
        for node in iter_out :
            ntype = type(node).__name__
            if ntype == 'BuiltinModule' :
                continue # ignore builtins
            # if the-edge-that-leads-to-node-represents-a-conditional-import:
            #   continue # ignore conditional imports
            node_tuple = (node_name(node), node.filename, 'PYMODULE')
            if node_tuple not in toc :
                # remember this import and look at its imports too
                toc.append(node_tuple)
                node_list.append(node)
'''

def find_PYZ_dependencies(config):
    logger.debug("Computing PYZ dependencies")
    ## We need to import `pyi_importers` from `PyInstaller` directory, but
    ## not from package `PyInstaller`
    #import PyInstaller.loader
    #a = PyInstaller.depend.imptracker.ImportTracker([
        #os.path.dirname(inspect.getsourcefile(PyInstaller.loader)),
        #os.path.join(HOMEPATH, 'support')])

    ## Frozen executable needs some modules bundled as bytecode objects ('PYMODULE' type)
    ## for the bootstrap process. The following lines ensures that.
    ## It's like making those modules 'built-in'.
    ## 'pyi_importers' is the base module that should be available as bytecode (co) object.
    #a.analyze_r('pyi_importers')
    #mod = a.modules['pyi_importers']
    #toc = build.TOC([(mod.__name__, mod.__file__, 'PYMODULE')])
    #for i, (nm, fnm, typ) in enumerate(toc):
        #mod = a.modules[nm]
        #tmp = []
        #for importednm, isdelayed, isconditional, level in mod.imports:
            #if not isconditional:
                #realnms = a.analyze_one(importednm, nm)
                #for realnm in realnms:
                    #imported = a.modules[realnm]
                    #if not isinstance(imported, PyInstaller.depend.modules.BuiltinModule):
                        #tmp.append((imported.__name__, imported.__file__, imported.typ))
        #toc.extend(tmp)
    #toc.reverse()

    # Import 'struct' modules to get real paths to module file names.
    mod1 = __import__('_struct')  # C extension.
    mod2 = __import__('struct')

    # Basic modules necessary for the bootstrap process.
    loader_mods = []

    # TODO - these hard-coded paths to struct/_struct are bogus, need to
    # at least get the real platform-dependent ones out of the main graph?
    loaderpath = os.path.join(HOMEPATH, 'PyInstaller', 'loader')
    # On some platforms (Windows, Debian/Ubuntu) '_struct' module is a built-in module (linked statically)
    # and thus does not have attribute __file__.
    # TODO verify this __file__ check on windows.
    if hasattr(mod1, '__file__'):
        loader_mods =[('_struct', os.path.abspath(mod1.__file__), 'EXTENSION')]

    loader_mods +=[
        ('struct', os.path.abspath(mod2.__file__), 'PYMODULE'),
        ('pyi_os_path', os.path.join(loaderpath, 'pyi_os_path.pyc'), 'PYMODULE'),
        ('pyi_archive',  os.path.join(loaderpath, 'pyi_archive.pyc'), 'PYMODULE'),
        ('pyi_importers',  os.path.join(loaderpath, 'pyi_importers.pyc'), 'PYMODULE')
    ]
    toc = TOC(loader_mods)
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
