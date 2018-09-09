#-----------------------------------------------------------------------------
# Copyright (c) 2015-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for PyPubSub for Python 2.7
# Includes submodules of pubsub to handle the way
# pubsub may provide different versions of its API
# according to the order in which certain modules are imported.
#
# Tested under Python 2.7.10 wih PyPubSub 3.3

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules('pubsub')

# collect_submodules does not find `arg1` or `kwargs` because
# they are not packages, just folders without an `__init__.py`
# Thus they are invisible to ModuleGraph and must be included as data files

pubsub_datas = collect_data_files('pubsub', include_py_files=True)


def _match(dst):
    return "kwargs" in dst or "arg1" in dst

datas = [(src, dst) for src, dst in pubsub_datas if _match(dst)]
