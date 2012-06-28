#
# Copyright (C) 2012, Daniel Hyams
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


# This little sample application generates a plugin on the fly,
# and then tries to import it.


import os
import sys


# We first import a static plugin; the application might have
# certain plugins that it always loads.
try:
    print('Attempting to import static_plugin...')
    mdl = __import__('static_plugin')
except ImportError:
    raise SystemExit('Failed to import the static plugin.')


plugin_contents = """
print('DYNAMIC PLUGIN IMPORTED.')
print('This is some user-generated plugin that does not come into existence')
print('until the application starts, and other modules in the directory')
print('it will reside in happen to have been imported (like the')
print('static_plugin)')
"""


# Create the dynamic plugin in the same directory as the executable.
program_dir = os.path.abspath(sys.prefix)
plugin_filename = os.path.join(program_dir, 'dynamic_plugin.py')
fp = open(plugin_filename, 'w')
fp.write(plugin_contents)
fp.close()


# Try import dynamic plugin.
try:
    print('Attempting to import dynamic_plugin...')
    mdl = __import__('dynamic_plugin')
except ImportError:
    raise SystemExit('Failed to import the dynamic plugin.')
finally:
    # Clean up. Remove files dynamic_plugin.py[c]
    try:
        os.remove(plugin_filename)
    except OSError:
        pass
    try:
        os.remove(plugin_filename + 'c')
    except OSError:
        pass
