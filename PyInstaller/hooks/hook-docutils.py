#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from hookutils import collect_submodules, collect_data_files

def hook(mod):
    global hiddenimports, datas
    hiddenimports = (collect_submodules('docutils.languages') +
                     collect_submodules('docutils.writers') +
                     collect_submodules('docutils.parsers.rst.languages') +
                     collect_submodules('docutils.parsers.rst.directives'))
    datas = collect_data_files('docutils')
    return mod
