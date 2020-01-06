# ----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# ----------------------------------------------------------------------------
import os
import re

from ..hooks import collect_submodules, collect_system_data_files, eval_statement, exec_statement
from ... import log as logging
from ...compat import base_prefix, is_darwin, is_win, open_file, \
    text_read_mode, text_type
from ...depend.bindepend import findSystemLibrary

logger = logging.getLogger(__name__)


def get_typelibs(module, version):
    """deprecated; only here for backwards compat.
    """
    logger.warning("get_typelibs is deprecated, use get_gi_typelibs instead")
    return get_gi_typelibs(module, version)[1]


def get_gi_libdir(module, version):
    statement = """
        import gi
        gi.require_version("GIRepository", "2.0")
        from gi.repository import GIRepository
        repo = GIRepository.Repository.get_default()
        module, version = (%r, %r)
        repo.require(module, version,
                     GIRepository.RepositoryLoadFlags.IREPOSITORY_LOAD_FLAG_LAZY)
        print(repo.get_shared_library(module))
    """
    statement %= (module, version)
    libs = exec_statement(statement).split(',')
    for lib in libs:
        path = findSystemLibrary(lib.strip())
        return os.path.normpath(os.path.dirname(path))

    raise ValueError("Could not find libdir for %s-%s" % (module, version))


def get_gi_typelibs(module, version):
    """
    Return a tuple of (binaries, datas, hiddenimports) to be used by PyGObject
    related hooks. Searches for and adds dependencies recursively.

    :param module: GI module name, as passed to 'gi.require_version()'
    :param version: GI module version, as passed to 'gi.require_version()'
    """
    datas = []
    binaries = []
    hiddenimports = []

    statement = """
        import gi
        gi.require_version("GIRepository", "2.0")
        from gi.repository import GIRepository
        repo = GIRepository.Repository.get_default()
        module, version = (%r, %r)
        repo.require(module, version,
                     GIRepository.RepositoryLoadFlags.IREPOSITORY_LOAD_FLAG_LAZY)
        get_deps = getattr(repo, 'get_immediate_dependencies', None)
        if not get_deps:
            get_deps = repo.get_dependencies
        print({'sharedlib': repo.get_shared_library(module),
               'typelib': repo.get_typelib_path(module),
               'deps': get_deps(module) or []})
    """
    statement %= (module, version)
    typelibs_data = eval_statement(statement)
    if not typelibs_data:
        logger.error("gi repository 'GIRepository 2.0' not found. "
                     "Please make sure libgirepository-gir2.0 resp. "
                     "lib64girepository-gir2.0 is installed.")
        # :todo: should we raise a SystemError here?
    else:
        logger.debug("Adding files for %s %s", module, version)

        if typelibs_data['sharedlib']:
            for lib in typelibs_data['sharedlib'].split(','):
                path = findSystemLibrary(lib.strip())
                if path:
                    logger.debug('Found shared library %s at %s', lib, path)
                    binaries.append((path, '.'))

        d = gir_library_path_fix(typelibs_data['typelib'])
        if d:
            logger.debug('Found gir typelib at %s', d)
            datas.append(d)

        hiddenimports += collect_submodules('gi.overrides',
                           lambda name: name.endswith('.' + module))

        # Load dependencies recursively
        for dep in typelibs_data['deps']:
            m, _ = dep.rsplit('-', 1)
            hiddenimports += ['gi.repository.%s' % m]

    return binaries, datas, hiddenimports


def gir_library_path_fix(path):
    import subprocess
    # 'PyInstaller.config' cannot be imported as other top-level modules.
    from ...config import CONF

    path = os.path.abspath(path)

    # On OSX we need to recompile the GIR files to reference the loader path,
    # but this is not necessary on other platforms
    if is_darwin:

        # If using a virtualenv, the base prefix and the path of the typelib
        # have really nothing to do with each other, so try to detect that
        common_path = os.path.commonprefix([base_prefix, path])
        if common_path == '/':
            logger.debug("virtualenv detected? fixing the gir path...")
            common_path = os.path.abspath(os.path.join(path, '..', '..', '..'))

        gir_path = os.path.join(common_path, 'share', 'gir-1.0')

        typelib_name = os.path.basename(path)
        gir_name = os.path.splitext(typelib_name)[0] + '.gir'

        gir_file = os.path.join(gir_path, gir_name)

        if not os.path.exists(gir_path):
            logger.error('Unable to find gir directory: %s.\n'
                         'Try installing your platforms gobject-introspection '
                         'package.', gir_path)
            return None
        if not os.path.exists(gir_file):
            logger.error('Unable to find gir file: %s.\n'
                         'Try installing your platforms gobject-introspection '
                         'package.', gir_file)
            return None

        with open_file(gir_file, text_read_mode, encoding='utf-8') as f:
            lines = f.readlines()
        # GIR files are `XML encoded <https://developer.gnome.org/gi/stable/gi-gir-reference.html>`_,
        # which means they are by definition encoded using UTF-8.
        with open_file(os.path.join(CONF['workpath'], gir_name), 'w',
                       encoding='utf-8') as f:
            for line in lines:
                if 'shared-library' in line:
                    split = re.split('(=)', line)
                    files = re.split('(["|,])', split[2])
                    for count, item in enumerate(files):
                        if 'lib' in item:
                            files[count] = '@loader_path/' + os.path.basename(item)
                    line = ''.join(split[0:2]) + ''.join(files)
                f.write(text_type(line))

        # g-ir-compiler expects a file so we cannot just pipe the fixed file to it.
        command = subprocess.Popen(('g-ir-compiler', os.path.join(CONF['workpath'], gir_name),
                                    '-o', os.path.join(CONF['workpath'], typelib_name)))
        command.wait()

        return os.path.join(CONF['workpath'], typelib_name), 'gi_typelibs'
    else:
        return path, 'gi_typelibs'


def get_glib_system_data_dirs():
    statement = """
        import gi
        gi.require_version('GLib', '2.0')
        from gi.repository import GLib
        print(GLib.get_system_data_dirs())
    """
    data_dirs = eval_statement(statement)
    if not data_dirs:
        logger.error("gi repository 'GIRepository 2.0' not found. "
                     "Please make sure libgirepository-gir2.0 resp. "
                     "lib64girepository-gir2.0 is installed.")
        # :todo: should we raise a SystemError here?
    return data_dirs


def get_glib_sysconf_dirs():
    """Try to return the sysconf directories, eg /etc."""
    if is_win:
        # On windows, if you look at gtkwin32.c, sysconfdir is actually
        # relative to the location of the GTK DLL. Since that's what
        # we're actually interested in (not the user path), we have to
        # do that the hard way'''
        return [os.path.join(get_gi_libdir('GLib', '2.0'), 'etc')]

    statement = """
        import gi
        gi.require_version('GLib', '2.0')
        from gi.repository import GLib
        print(GLib.get_system_config_dirs())
    """
    data_dirs = eval_statement(statement)
    if not data_dirs:
        logger.error("gi repository 'GIRepository 2.0' not found. "
                     "Please make sure libgirepository-gir2.0 resp. "
                     "lib64girepository-gir2.0 is installed.")
        # :todo: should we raise a SystemError here?
    return data_dirs


def collect_glib_share_files(*path):
    """path is relative to the system data directory (eg, /usr/share)"""
    glib_data_dirs = get_glib_system_data_dirs()
    if glib_data_dirs is None:
        return []

    destdir = os.path.join('share', *path[:-1])

    # TODO: will this return too much?
    collected = []
    for data_dir in glib_data_dirs:
        p = os.path.join(data_dir, *path)
        collected += collect_system_data_files(p, destdir=destdir, include_py_files=False)

    return collected


def collect_glib_etc_files(*path):
    """path is relative to the system config directory (eg, /etc)"""
    glib_config_dirs = get_glib_sysconf_dirs()
    if glib_config_dirs is None:
        return []

    destdir = os.path.join('etc', *path[:-1])

    # TODO: will this return too much?
    collected = []
    for config_dir in glib_config_dirs:
        p = os.path.join(config_dir, *path)
        collected += collect_system_data_files(p, destdir=destdir, include_py_files=False)

    return collected

_glib_translations = None


def collect_glib_translations(prog):
    """
    Return a list of translations in the system locale directory whose names equal prog.mo.
    """
    global _glib_translations
    if _glib_translations is None:
        _glib_translations = collect_glib_share_files('locale')

    names = [os.sep + prog + '.mo',
             os.sep + prog + '.po']
    namelen = len(names[0])

    return [(src, dst) for src, dst in _glib_translations if src[-namelen:] in names]

__all__ = ('get_typelibs', 'get_gi_libdir', 'get_gi_typelibs', 'gir_library_path_fix', 'get_glib_system_data_dirs',
           'get_glib_sysconf_dirs', 'collect_glib_share_files', 'collect_glib_etc_files', 'collect_glib_translations')
