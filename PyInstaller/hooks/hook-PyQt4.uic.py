#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Because this is PyQt4.uic, note the fully qualified package name required in
# order to refer to PyInstaller.utils.hooks.
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
from PyInstaller.compat import is_linux

# On Linux PyQt4.uic might use the PyKDE4 package for some rendering. If it
# isn't installed, the the following exception is raised::
#
#      File "/usr/local/lib/python2.7/dist-packages/PyInstaller-2.1.1dev_9e9d21b-py2.7.egg/PyInstaller/hooks/hook-PyQt4.uic.py", line 29, in <module>
#        hiddenimports += collect_submodules('PyKDE4') + ['PyQt4.QtSvg', 'PyQt4.QtXml']
#      File "/usr/local/lib/python2.7/dist-packages/PyInstaller-2.1.1dev_9e9d21b-py2.7.egg/PyInstaller/utils/hooks/__init__.py", line 679, in collect_submodules
#        pkg_base, pkg_dir = get_package_paths(package)
#      File "/usr/local/lib/python2.7/dist-packages/PyInstaller-2.1.1dev_9e9d21b-py2.7.egg/PyInstaller/utils/hooks/__init__.py", line 646, in get_package_paths
#        assert is_package, 'Package %s does not have __path__ attribute' % package
#    AssertionError: Package PyKDE4 does not have __path__ attribute
#
# Therefeore, catch this exception and ignore it. When this happends, a message
# is still generated::
#
#    2141 INFO: Processing hook hook-PyQt4.QtCore
#    Traceback (most recent call last):
#      File "<string>", line 1, in <module>
#    ImportError: No module named PyKDE4
#    2862 INFO: Processing hook hook-PyQt4.uic
#
# Note that the warning comes BEFORE hook-PyQt4.uic is listed, not after;
# however, the raised assertion caught by the try/except block below produces
# it, not any code in hook-PyQt4.QtCore.
if is_linux:
    try:
        hiddenimports = collect_submodules('PyKDE4') + ['PyQt4.QtSvg', 'PyQt4.QtXml']
    except AssertionError:
        pass
# Need to include modules in PyQt4.uic.widget-plugins, so they can be
# dynamically loaded by uic. They should both be included as separate
# (data-like) files, so they can be found by os.listdir and friends. However,
# this directory isn't a package, refer to it using the package (PyQt4.uic)
# followed by the subdirectory name (widget-plugins/).
datas = collect_data_files('PyQt4.uic', True, 'widget-plugins')
