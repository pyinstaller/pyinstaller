# -----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from jupyter_core.paths import ENV_JUPYTER_PATH, ENV_CONFIG_PATH

# collect modules for handlers
hiddenimports = collect_submodules('notebook', filter=lambda name: name.endswith('.handles'))
hiddenimports.append('notebook.services.shutdown')

datas = collect_data_files('notebook')

# Collect share and etc folder for pre-installed extensions
datas += [(path, 'share/jupyter') for path in ENV_JUPYTER_PATH]
datas += [(path, 'etc/jupyter') for path in ENV_CONFIG_PATH]
