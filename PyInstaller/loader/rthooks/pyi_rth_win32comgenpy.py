#
# Copyright (C) 2012, Martin Zibricky
# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# In addition to the permissions in the GNU General Public License, the
# authors give you unlimited permission to link or embed the compiled
# version of this file into combinations with other programs, and to
# distribute those combinations without any restriction coming from the
# use of this file. (The General Public License restrictions do apply in
# other respects; for example, they cover modification of the file, and
# distribution when not linked into a combine executable.)
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA


# The win32.client.gencache code must be allowed to create the cache in %temp%
# (user's temp). It is necessary to get the gencache code to use a suitable
# directory other than the default in lib\site-packages\win32com\client\gen_py.
# PyInstaller does not provide this directory structure and the frozen
# executable could be placed in a non-writable directory like 'C:\Program Files.
# That's the reason for %temp% directory.
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


# Create 'gen_py' directory. This directory does not need
# to contain '__init__.py' file.
try:
    # win32com gencache cannot be put directly to 'supportdir' with any
    # random name. It has to be put in a directory called 'gen_py'.
    # This is the reason why to create this directory in supportdir'.
    os.makedirs(genpydir)
    # Remove temp directory at application exit and ignore any errors.
    atexit.register(shutil.rmtree, supportdir, ignore_errors=True)
except OSError:
    pass


# Override the default path to gen_py cache.
import win32com
win32com.__gen_path__ = genpydir


# Ensure genpydir is in 'gen_py' module paths.
import win32com.gen_py
win32com.gen_py.__path__.insert(0, genpydir)
