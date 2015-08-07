#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Code related to processing of import hooks.
"""


import collections
import glob
import os.path


class HooksCache(collections.UserDict):
    """
    Implements cache of module list for which there exists a hook.
    It allows to iterate over import hooks and remove them.
    """
    def __init__(self, hooks_path):
        """
        :param hooks_path: File name where to load hook from.
        """
        # Initializes self.data that contains the real dictionary.
        super(HooksCache, self).__init__()
        self._load_file_list(hooks_path)

    def _load_file_list(self, path):
        """
        Internal method list directory and update the list of available hooks.
        """
        files = glob.glob(os.path.join(path, 'hook-*.py'))
        for f in files:
            # Remove prefix 'hook-' and suffix '.py'.
            modname = os.path.basename(f)[5:-3]
            f = os.path.abspath(f)
            # key - module name, value - path to hook directory.
            self.data[modname] = f

    def add_custom_paths(self, custom_paths):
        for p in custom_paths:
            self._load_file_list(p)

    def remove(self, names):
        """
        :param names: List of module names to remove from cache.
        """
        names = set(names)  # Eliminate duplicate entries.
        for n in names:
            if n in self.data:
                del self.data[n]


class ImportHook(object):
    """
    Class encapsulating processing of hook attributes like hiddenimports, etc.
    """
    def __init__(self, modname, hook_filename):
        """
        :param hook_filename: File name where to load hook from.
        """
        pass
        # TODO
        pass

    def load(self):
        """
        Load hook from file and parse and interpret it's content.
        """
        # TODO
        pass

    def update_dependencies(self, mod_graph):
        """
        Update module dependency graph with import hook attributes (hiddenimports, etc.)
        :param mod_graph: PyiModuleGraph object to be updated.
        :return: dict with additional files that were defined in hook file (datas, binaries)
        """
        files = {'binaries': [],
                 'datas': []}
        # TODO
        pass
