#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for wxPython 2.8.x, 2.9.x, and 3.0.x for Python 2.7.
# Includes submodules of wx.lib.pubsub to handle the way
# wx.lib.pubsub may provide different versions of its API
# according to the order in which certain modules are imported.

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules('wx.lib.pubsub')

# collect_submodules does not find `pubsub1` or `pubsub2` because
# they are not packages, just folders without an `__init__.py`
# Thus they are invisible to ModuleGraph and must be included as data files

pubsub_datas = collect_data_files('wx.lib.pubsub', include_py_files=True)

def _match(src, dst):
    # Since ``pubsub1`` and ``pubsub2`` are directories, they should be in dst.
    # However, ``autosetuppubsubv1`` is a ``.py`` file, so it will only appear
    # in the ``src``. For example::
    #
    #     pubsub_datas = [('c:\\python27\\lib\\site-packages\\wx-2.8-msw-unicode\\wx\\lib\\pubsub\\autosetuppubsubv1.py',
    #       'wx\\lib\\pubsub') ]
    return "pubsub1" in dst or "pubsub2" in dst or "autosetuppubsubv1" in src

datas = [(src, dst) for src, dst in pubsub_datas if _match(src, dst)]
