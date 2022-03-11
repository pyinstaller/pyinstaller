#-----------------------------------------------------------------------------
# Copyright (c) 2013-2022, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

# The win32.client.gencache code must be allowed to create the cache in %temp% (user's temp). It is necessary to get the
# gencache code to use a suitable directory other than the default in lib\site-packages\win32com\client\gen_py.
# PyInstaller does not provide this directory structure and the frozen executable could be placed in a non-writable
# directory like 'C:\Program Files. That's the reason for %temp% directory.
#
# http://www.py2exe.org/index.cgi/UsingEnsureDispatch

import atexit
import os
import shutil
import tempfile

# Put gen_py cache in temp directory.
supportdir = tempfile.mkdtemp()
# gen_py has to be put into directory 'gen_py'.
genpydir = os.path.join(supportdir, 'gen_py')

# Create 'gen_py' directory. This directory does not need to contain '__init__.py' file.
try:
    # win32com gencache cannot be put directly to 'supportdir' with any random name. It has to be put in a directory
    # called 'gen_py'. This is the reason why to create this directory in supportdir'.
    os.makedirs(genpydir)
    # Remove temp directory at application exit and ignore any errors.
    atexit.register(shutil.rmtree, supportdir, ignore_errors=True)
except OSError:
    pass

# Override the default path to gen_py cache.
import win32com  # noqa: E402

win32com.__gen_path__ = genpydir

# The attribute __loader__ makes module 'pkg_resources' working but On Windows it breaks pywin32 (win32com) and test
# 'basic/test_pyttsx' will fail. Just removing that attribute for win32com fixes that and gencache is created properly.
if hasattr(win32com, '__loader__'):
    del win32com.__loader__

# Ensure genpydir is in 'gen_py' module paths.
import win32com.gen_py  # noqa: E402

win32com.gen_py.__path__.insert(0, genpydir)
