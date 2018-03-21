#-----------------------------------------------------------------------------
# Copyright (c) 2015-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from __future__ import print_function

from pyi_testmod_metapath1.extern import aaa   # __import__ below works
#import pyi_testmod_metapath1.extern           # __import__ below works
#import pyi_testmod_metapath1.extern.aaa       # __import__ below fails!
__import__('pyi_testmod_metapath1.extern.bbb')

try:
    bbb = pyi_testmod_metapath1.extern.bbb
except NameError:
    pass
else:
    print("name:", bbb.__name__)
    print("__file__:", bbb.__file__ or repr(bbb.__file__))
    assert bbb.__name__.endswith('._vendor.bbb')


# Second test: import sub-sub-package
# Mimic this lines from pkg_resources.__init__.py as of setuptools 28.6.1:
#   from pkg_resources.extern import packaging
#   __import__('pkg_resources.extern.packaging.version')
from pyi_testmod_metapath1.extern import ccc
__import__('pyi_testmod_metapath1.extern.ccc.ddd')

try:
    ddd = pyi_testmod_metapath1.extern.ccc.ddd
except NameError:
    pass
else:
    print("name:", ddd.__name__)
    print("__file__:", ddd.__file__ or repr(ddd.__file__))
    assert ddd.__name__.endswith('._vendor.ccc.ddd')

# Third test: import sub-sub-sub-package
__import__('pyi_testmod_metapath1.extern.ccc.eee.fff')
