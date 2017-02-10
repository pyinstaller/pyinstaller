# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Library imports
# ---------------

# Third-party imports
# -------------------

# Local imports
# -------------
from PyInstaller.compat import is_py2
from PyInstaller.utils.tests import skipif

@skipif(not is_py2, reason='Only needed on Python 2')
def test_Queue_queue(pyi_builder):
    pyi_builder.test_source("""
        import queue
        queue.Queue()
        """)
