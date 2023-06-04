# Copyright (C) 2017-2023 PyInstaller Development Team.
# Copyright (C) 2016 Jason R Coombs <jaraco@jaraco.com>
#
# This file includes an almost complete copy of
# setuptools/extern/__init__.py, taken from setuptools 67.8.0.
# For PyInstaller the only change is to install a sub-class of VendorImporter,
# and that the source is auto-formatted using yapf.
#
# setuptools is licensed under the MIT License (expat) license:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
# SPDX-License-Identifier: MIT

#--- Code of setuptools/extern/__init__.py starts here
import importlib.util
import sys


class VendorImporter:
    """
    A PEP 302 meta path importer for finding optionally-vendored or otherwise naturally-installed
    packages from root_name.
    """
    def __init__(self, root_name, vendored_names=(), vendor_pkg=None):
        self.root_name = root_name
        self.vendored_names = set(vendored_names)
        self.vendor_pkg = vendor_pkg or root_name.replace('extern', '_vendor')

    @property
    def search_path(self):
        """
        Search first the vendor package then as a natural package.
        """
        yield self.vendor_pkg + '.'
        yield ''

    def _module_matches_namespace(self, fullname):
        """Figure out if the target module is vendored."""
        root, base, target = fullname.partition(self.root_name + '.')
        return not root and any(map(target.startswith, self.vendored_names))

    def load_module(self, fullname):
        """
        Iterate over the search path to locate and load fullname.
        """
        root, base, target = fullname.partition(self.root_name + '.')
        for prefix in self.search_path:
            try:
                extant = prefix + target
                __import__(extant)
                mod = sys.modules[extant]
                sys.modules[fullname] = mod
                return mod
            except ImportError:
                pass
        else:
            raise ImportError(
                "The '{target}' package is required; normally this is bundled with this package so if you get "
                "this warning, consult the packager of your distribution.".format(**locals())
            )

    def create_module(self, spec):
        return self.load_module(spec.name)

    def exec_module(self, module):
        pass

    def find_spec(self, fullname, path=None, target=None):
        """Return a module spec for vendored names."""
        return importlib.util.spec_from_loader(fullname, self) if self._module_matches_namespace(fullname) else None

    def install(self):
        """
        Install this importer into sys.meta_path if not already present.
        """
        if self not in sys.meta_path:
            sys.meta_path.append(self)


# --- Code of setuptools/extern/__init__.py ends here


class MyVendorImporter(VendorImporter):
    @property
    def search_path(self):
        """
        Only search the vendor package, and not a natural package.
        """
        yield self.vendor_pkg + '.'


names = ('aaa', 'bbb', 'ccc')
MyVendorImporter(__name__, names).install()
