#-----------------------------------------------------------------------------
# Copyright (c) 2015-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
# CherryPy is a minimalist Python web framework.
#
# http://www.cherrypy.org/
#
# Tested with CherryPy 5.0.1


from PyInstaller.utils.hooks import collect_submodules


hiddenimports = collect_submodules('cherrypy.wsgiserver')