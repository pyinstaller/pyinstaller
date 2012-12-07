#
# Copyright (C) 2012, Martin Zibricky
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


# This is a fake 'site' module available in default Python Library.
#
# The real 'site' does some magic to find paths to other possible
# Python modules. We do not want this behaviour for frozen applications.
#
# Fake 'site' makes PyInstaller to work with distutils and to work inside
# virtualenv environment.


# TODO test the following code stub from real 'site' module.


# Prefixes for site-packages; add additional prefixes like /usr/local here
PREFIXES = []

# Enable per user site-packages directory
# set it to False to disable the feature or True to force the feature
ENABLE_USER_SITE = False


# For distutils.commands.install
# These values are initialized by the getuserbase() and getusersitepackages()
# functions, through the main() function when Python starts.
USER_SITE = None
USER_BASE = None


# Package IPython depends on the following functionality from real site.py.
# This code could be probably removed when the following bug is fixed:
# https://github.com/ipython/ipython/issues/2606
class _Helper(object):
     """
     Define the builtin 'help'.
     This is a wrapper around pydoc.help (with a twist).
     """
     def __repr__(self):
         return "Type help() for interactive help, " \
                "or help(object) for help about object."
     def __call__(self, *args, **kwds):
         import pydoc
         return pydoc.help(*args, **kwds)
