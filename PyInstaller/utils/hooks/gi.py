# ----------------------------------------------------------------------------
# Copyright (c) 2005-2022, PyInstaller Development Team.
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

from PyInstaller.utils.hooks import collect_submodules, collect_system_data_files, get_hook_config
from PyInstaller import isolated
from PyInstaller import log as logging
from PyInstaller import compat
from PyInstaller.depend.bindepend import findSystemLibrary

logger = logging.getLogger(__name__)


class GiModuleInfo:
    def __init__(self, module, version, hook_api=None):
        self.name = module
        self.version = version
        self.available = False
        self.sharedlibs = []
        self.typelib = None
        self.dependencies = []

        # If hook API is available, use it to override the version from hookconfig.
        if hook_api is not None:
            module_versions = get_hook_config(hook_api, 'gi', 'module-versions')
            if module_versions:
                version = module_versions.get(module, version)

        logger.debug("Gathering GI module info for %s %s", module, version)

        @isolated.decorate
        def _get_module_info(module, version):
            import gi
            gi.require_version("GIRepository", "2.0")
            from gi.repository import GIRepository

            repo = GIRepository.Repository.get_default()
            repo.require(module, version, GIRepository.RepositoryLoadFlags.IREPOSITORY_LOAD_FLAG_LAZY)

            # Shared library/libraries
            # Comma-separated list of paths to shared libraries, or None if none are associated. Convert to list.
            sharedlibs = repo.get_shared_library(module)
            sharedlibs = [lib.strip() for lib in sharedlibs.split(",")] if sharedlibs else []

            # Path to .typelib file
            typelib = repo.get_typelib_path(module)

            # Dependencies
            # GIRepository.Repository.get_immediate_dependencies is available from gobject-introspection v1.44 on
            if hasattr(repo, 'get_immediate_dependencies'):
                dependencies = repo.get_immediate_dependencies(module)
            else:
                dependencies = repo.get_dependencies(module)

            return {
                'sharedlibs': sharedlibs,
                'typelib': typelib,
                'dependencies': dependencies,
            }

        # Try to query information; if this fails, mark module as unavailable.
        try:
            info = _get_module_info(module, version)
            self.sharedlibs = info['sharedlibs']
            self.typelib = info['typelib']
            self.dependencies = info['dependencies']
            self.available = True
        except Exception as e:
            logger.debug("Failed to query GI module %s %s: %s", module, version, e)
            self.available = False

    def get_libdir(self):
        """
        Return the path to shared library used by the module. If no libraries are associated with the typelib, None is
        returned. If multiple library names are associated with the typelib, the path to the first resolved shared
        library is returned. Raises exception if module is unavailable or none of the shared libraries could be
        resolved.
        """
        # Module unavailable
        if not self.available:
            raise ValueError(f"Module {self.name} {self.version} is unavailable!")
        # Module has no associated shared libraries
        if not self.sharedlibs:
            return None
        for lib in self.sharedlibs:
            path = findSystemLibrary(lib)
            if path:
                return os.path.normpath(os.path.dirname(path))
        raise ValueError(f"Could not resolve any shared library of {self.name} {self.version}: {self.sharedlibs}!")

    def collect_typelib_data(self):
        """
        Return a tuple of (binaries, datas, hiddenimports) to be used by PyGObject related hooks.
        """
        datas = []
        binaries = []
        hiddenimports = []

        logger.debug("Collecting module data for %s %s", self.name, self.version)

        # Module unavailable
        if not self.available:
            raise ValueError(f"Module {self.name} {self.version} is unavailable!")

        # Find shared libraries
        for lib in self.sharedlibs:
            lib_path = findSystemLibrary(lib)
            if lib_path:
                logger.debug('Collecting shared library %s at %s', lib, lib_path)
                binaries.append((lib_path, '.'))

        # Find and collect .typelib file. Run it through the `gir_library_path_fix` to fix the library path, if
        # necessary.
        typelib_entry = gir_library_path_fix(self.typelib)
        if typelib_entry:
            logger.debug('Collecting gir typelib at %s', typelib_entry[0])
            datas.append(typelib_entry)

        # Overrides for the module
        hiddenimports += collect_submodules('gi.overrides', lambda name: name.endswith('.' + self.name))

        # Module dependencies
        for dep in self.dependencies:
            dep_module, _ = dep.rsplit('-', 1)
            hiddenimports += [f'gi.repository.{dep_module}']

        return binaries, datas, hiddenimports


# The old function, provided for backwards compatibility in 3rd party hooks.
def get_gi_libdir(module, version):
    module_info = GiModuleInfo(module, version)
    return module_info.get_libdir()


# The old function, provided for backwards compatibility in 3rd party hooks.
def get_gi_typelibs(module, version):
    """
    Return a tuple of (binaries, datas, hiddenimports) to be used by PyGObject related hooks. Searches for and adds
    dependencies recursively.

    :param module: GI module name, as passed to 'gi.require_version()'
    :param version: GI module version, as passed to 'gi.require_version()'
    """
    module_info = GiModuleInfo(module, version)
    return module_info.collect_typelib_data()


def gir_library_path_fix(path):
    import subprocess

    # 'PyInstaller.config' cannot be imported as other top-level modules.
    from PyInstaller.config import CONF

    path = os.path.abspath(path)

    # On Mac OS we need to recompile the GIR files to reference the loader path,
    # but this is not necessary on other platforms.
    if compat.is_darwin:

        # If using a virtualenv, the base prefix and the path of the typelib
        # have really nothing to do with each other, so try to detect that.
        common_path = os.path.commonprefix([compat.base_prefix, path])
        if common_path == '/':
            logger.debug("virtualenv detected? fixing the gir path...")
            common_path = os.path.abspath(os.path.join(path, '..', '..', '..'))

        gir_path = os.path.join(common_path, 'share', 'gir-1.0')

        typelib_name = os.path.basename(path)
        gir_name = os.path.splitext(typelib_name)[0] + '.gir'

        gir_file = os.path.join(gir_path, gir_name)

        if not os.path.exists(gir_path):
            logger.error(
                "Unable to find gir directory: %s.\nTry installing your platform's gobject-introspection package.",
                gir_path
            )
            return None
        if not os.path.exists(gir_file):
            logger.error(
                "Unable to find gir file: %s.\nTry installing your platform's gobject-introspection package.", gir_file
            )
            return None

        with open(gir_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # GIR files are `XML encoded <https://developer.gnome.org/gi/stable/gi-gir-reference.html>`_,
        # which means they are by definition encoded using UTF-8.
        with open(os.path.join(CONF['workpath'], gir_name), 'w', encoding='utf-8') as f:
            for line in lines:
                if 'shared-library' in line:
                    split = re.split('(=)', line)
                    files = re.split('(["|,])', split[2])
                    for count, item in enumerate(files):
                        if 'lib' in item:
                            files[count] = '@loader_path/' + os.path.basename(item)
                    line = ''.join(split[0:2]) + ''.join(files)
                f.write(line)

        # g-ir-compiler expects a file so we cannot just pipe the fixed file to it.
        command = subprocess.Popen((
            'g-ir-compiler', os.path.join(CONF['workpath'], gir_name),
            '-o', os.path.join(CONF['workpath'], typelib_name)
        ))  # yapf: disable
        command.wait()

        return os.path.join(CONF['workpath'], typelib_name), 'gi_typelibs'
    else:
        return path, 'gi_typelibs'


@isolated.decorate
def get_glib_system_data_dirs():
    import gi
    gi.require_version('GLib', '2.0')
    from gi.repository import GLib
    return GLib.get_system_data_dirs()


def get_glib_sysconf_dirs():
    """
    Try to return the sysconf directories (e.g., /etc).
    """
    if compat.is_win:
        # On Windows, if you look at gtkwin32.c, sysconfdir is actually relative to the location of the GTK DLL. Since
        # that is what we are actually interested in (not the user path), we have to do that the hard way...
        return [os.path.join(get_gi_libdir('GLib', '2.0'), 'etc')]

    @isolated.call
    def data_dirs():
        import gi
        gi.require_version('GLib', '2.0')
        from gi.repository import GLib
        return GLib.get_system_config_dirs()

    return data_dirs


def collect_glib_share_files(*path):
    """
    Path is relative to the system data directory (e.g., /usr/share).
    """
    glib_data_dirs = get_glib_system_data_dirs()
    if glib_data_dirs is None:
        return []

    destdir = os.path.join('share', *path)

    # TODO: will this return too much?
    collected = []
    for data_dir in glib_data_dirs:
        p = os.path.join(data_dir, *path)
        collected += collect_system_data_files(p, destdir=destdir, include_py_files=False)

    return collected


def collect_glib_etc_files(*path):
    """
    Path is relative to the system config directory (e.g., /etc).
    """
    glib_config_dirs = get_glib_sysconf_dirs()
    if glib_config_dirs is None:
        return []

    destdir = os.path.join('etc', *path)

    # TODO: will this return too much?
    collected = []
    for config_dir in glib_config_dirs:
        p = os.path.join(config_dir, *path)
        collected += collect_system_data_files(p, destdir=destdir, include_py_files=False)

    return collected


_glib_translations = None


def collect_glib_translations(prog, lang_list=None):
    """
    Return a list of translations in the system locale directory whose names equal prog.mo.
    """
    global _glib_translations
    if _glib_translations is None:
        if lang_list is not None:
            trans = []
            for lang in lang_list:
                trans += collect_glib_share_files(os.path.join("locale", lang))
            _glib_translations = trans
        else:
            _glib_translations = collect_glib_share_files('locale')

    names = [os.sep + prog + '.mo', os.sep + prog + '.po']
    namelen = len(names[0])

    return [(src, dst) for src, dst in _glib_translations if src[-namelen:] in names]
