#-----------------------------------------------------------------------------
# Copyright (c) 2005-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# This hook handles for the infamous _xmlplus hack
# http://www.amk.ca/diary/2003/03/pythons__xmlplus_hack.html (outdated URL)
#
# If the `xml` package is able to import `_xmlplus`, it a) replaces
# itself by the `_xmlplus_` module and b) appends it's own `__path__`
# to the `__path__` of `_xmlplus`. Thus modules in `_xmlplus` have
# precedence, but fall back is `xml`.
#
# In PyInstaller (a) is handled by modulegraph and (b) by this hook.
#
# Note 1: `_xmlplus` is from the PyXML package, whch is no longer
#         maintained.
# Note 2: This hack has been removed for Python 3.1, see
#         https://bugs.python.org/issue11164
#
# :todo: This hook should be removed in a few years or when
# PyInstaller is dropping support for Python 2.7.  2015-11-06
#

def pre_safe_import_module(api):
    # preserve path of existing `xml` package
    for p in api.module_graph.findNode('xml').packagepath:
        # Append to package path of module `xml`, since this is the
        # name which will be used in modulegraph.
        api.module_graph.append_package_path('xml', p)
