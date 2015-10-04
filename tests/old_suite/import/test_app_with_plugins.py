#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


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
print('This is some user-generated plugin that does not exist until')
print('  the application starts and other modules in the directory')
print('  are imported (like the static_plugin).')
"""


# Create the dynamic plugin in the same directory as the executable.
if hasattr(sys, 'frozen'):
    program_dir = os.path.abspath(sys.prefix)
else:
    program_dir = os.path.dirname(os.path.abspath(__file__))
plugin_filename = os.path.join(program_dir, 'dynamic_plugin.py')
fp = open(plugin_filename, 'w')
fp.write(plugin_contents)
fp.close()


# Try import dynamic plugin.
is_error = False
try:
    print('Attempting to import dynamic_plugin...')
    mdl = __import__('dynamic_plugin')
except ImportError:
    is_error = True


# Clean up. Remove files dynamic_plugin.py[c]
for f in (plugin_filename, plugin_filename + 'c'):
    try:
        os.remove(plugin_filename)
    except OSError:
        pass


# Statement 'try except finally' is available since Python 2.5+.
if is_error:
    # Raise exeption.
    raise SystemExit('Failed to import the dynamic plugin.')
