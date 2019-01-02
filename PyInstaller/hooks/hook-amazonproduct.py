#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Hook for Python bindings for Amazon's Product Advertising API.
https://bitbucket.org/basti/python-amazon-product-api
"""


hiddenimports = ['amazonproduct.processors.__init__',
                 'amazonproduct.processors._lxml',
                 'amazonproduct.processors.objectify',
                 'amazonproduct.processors.elementtree',
                 'amazonproduct.processors.etree',
                 'amazonproduct.processors.minidom',
                 'amazonproduct.contrib.__init__',
                 'amazonproduct.contrib.cart',
                 'amazonproduct.contrib.caching',
                 'amazonproduct.contrib.retry']