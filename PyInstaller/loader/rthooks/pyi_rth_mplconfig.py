#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# matplotlib will create $HOME/.matplotlib folder in user's home directory.
# In this directory there is fontList.cache file which lists paths
# to matplotlib fonts.
#
# When you run your onefile exe for the first time it's extracted to for example
# "_MEIxxxxx" temp directory and fontList.cache file is created with fonts paths
# pointing to this directory.
#
# Second time you run your exe new directory is created "_MEIyyyyy" but
# fontList.cache file still points to previous directory which was deleted.
# And then you will get error like:
#
#     RuntimeError: Could not open facefile
#
# We need to force matplotlib to recreate config directory every time you run
# your app.


import atexit
import os
import shutil
import tempfile


# Put matplot config dir to temp directory.
configdir = tempfile.mkdtemp()
os.environ['MPLCONFIGDIR'] = configdir


try:
    # Remove temp directory at application exit and ignore any errors.
    atexit.register(shutil.rmtree, configdir, ignore_errors=True)
except OSError:
    pass
