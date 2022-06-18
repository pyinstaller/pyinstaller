#-----------------------------------------------------------------------------
# Copyright (c) 2005-2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# GStreamer contains a lot of plugins. We need to collect them and bundle them with the exe file. We also need to
# resolve binary dependencies of these GStreamer plugins.

import glob
import os

from PyInstaller.utils.hooks import get_hook_config
import PyInstaller.log as logging
from PyInstaller import isolated
from PyInstaller.utils.hooks.gi import GiModuleInfo, collect_glib_share_files, collect_glib_translations

logger = logging.getLogger(__name__)


@isolated.decorate
def _get_gst_plugin_path():
    import os
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init(None)
    reg = Gst.Registry.get()
    plug = reg.find_plugin('coreelements')
    path = plug.get_filename()
    return os.path.dirname(path)


def hook(hook_api):
    module_info = GiModuleInfo('Gst', '1.0')
    if not module_info.available:
        return

    binaries, datas, hiddenimports = module_info.collect_typelib_data()
    hiddenimports += ["gi.repository.Gio"]

    # Collect data files
    datas += collect_glib_share_files('gstreamer-1.0')

    # Translations
    lang_list = get_hook_config(hook_api, "gi", "languages")
    for prog in [
        'gst-plugins-bad-1.0',
        'gst-plugins-base-1.0',
        'gst-plugins-good-1.0',
        'gst-plugins-ugly-1.0',
        'gstreamer-1.0',
    ]:
        datas += collect_glib_translations(prog, lang_list)

    # Plugins
    try:
        plugin_path = _get_gst_plugin_path()
    except Exception as e:
        logger.warning("Failed to determine gstreamer plugin path: %s", e)
        plugin_path = None

    if plugin_path:
        # Use a pattern of libgst* as all GStreamer plugins that conform to GStreamer standards start with libgst, and
        # we may have mixed plugin extensions, e.g., .so and .dylib.
        for lib_pattern in ['libgst*.dll', 'libgst*.dylib', 'libgst*.so']:
            pattern = os.path.join(plugin_path, lib_pattern)
            binaries += [(f, os.path.join('gst_plugins')) for f in glob.glob(pattern)]

    hook_api.add_datas(datas)
    hook_api.add_binaries(binaries)
    hook_api.add_imports(*hiddenimports)
