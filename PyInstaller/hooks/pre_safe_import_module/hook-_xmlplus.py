#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# This hook used to handle the infamous _xmlplus hack: If the `xml`
# package is able to import `_xmlplus`, it a) replaces itself by the
# `_xmlplus_` module and b) appends it's own `__path__` to the
# `__path__` of `_xmlplus`. Thus modules in `_xmlplus` have
# precedence, but fall back is `xml`.
#
# This hack has been removed for Python 3.1, see
# https://bugs.python.org/issue11164.
#
# `_xmlplus` is from the PyXML package, which is no longer maintained
# and not even compatible with Python 2.7 - even if some Linux
# distributions patched it for 2.7
#
# :todo: This hook should be removed in a few years or when
# PyInstaller is dropping support for Python 2.7.  2015-11-06
#

def pre_safe_import_module(api):
    raise SystemExit('PyXML and _xmlplus are outdated. Please get rid of it.')
