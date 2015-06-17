#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# This file is part of the package for testing eggs in `PyInstaller`.


from setuptools import setup

setup(name='unzipped_egg',
      version='0.1',
      description='A unzipped egg for testing PyInstaller',
      packages=['unzipped_egg'],
      package_data={'unzipped_egg': ['data/datafile.txt']},
      zip_safe = False,
     )
