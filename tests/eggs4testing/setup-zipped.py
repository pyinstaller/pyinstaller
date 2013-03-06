#!/usr/bin/env python
#
# This file is part of the package for testing eggs in `PyInstaller`.
#
# Author:    Hartmut Goebel <h.goebel@goebel-consult.de>
# Copyright: 2012 by Hartmut Goebel
# Licence:   GNU Public Licence v3 (GPLv3)
#

from setuptools import setup

setup(name='zipped_egg',
      version='0.1',
      description='A zipped egg for testing PyInstaller',
      packages=['zipped_egg'],
      package_data={'zipped_egg': ['data/datafile.txt']},
     )
