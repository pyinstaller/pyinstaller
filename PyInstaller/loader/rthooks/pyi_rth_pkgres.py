#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import pkg_resources as res
from pyimod03_importers import FrozenImporter


# To make pkg_resources work with froze moduels we need to set the 'Provider'
# class for FrozenImporter. This class decides where to look for resources
# and other stuff. 'pkg_resources.NullProvider' is dedicated to PEP302
# import hooks like FrozenImporter is. It uses method __loader__.get_data() in
# methods pkg_resources.resource_string() and pkg_resources.resource_stream()
res.register_loader_type(FrozenImporter, res.NullProvider)
