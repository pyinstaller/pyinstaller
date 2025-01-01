#-----------------------------------------------------------------------------
# Copyright (c) 2021-2023, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------


def _pyi_rthook():
    import inspect
    import os
    import sys
    import zipfile

    # Use sys._MEIPASS with normalized path component separator. This is necessary on some platforms (i.e., msys2/mingw
    # python on Windows), because we use string comparisons on the paths.
    SYS_PREFIX = os.path.normpath(sys._MEIPASS)
    BASE_LIBRARY = os.path.join(SYS_PREFIX, "base_library.zip")

    # Obtain the list of modules in base_library.zip, so we can use it in our `_pyi_getsourcefile` implementation.
    def _get_base_library_files(filename):
        # base_library.zip might not exit
        if not os.path.isfile(filename):
            return set()

        with zipfile.ZipFile(filename, 'r') as zf:
            namelist = zf.namelist()

        return set(os.path.normpath(entry) for entry in namelist)

    base_library_files = _get_base_library_files(BASE_LIBRARY)

    # Provide custom implementation of inspect.getsourcefile() for frozen applications that properly resolves relative
    # filenames obtained from object (e.g., inspect stack-frames). See #5963.
    #
    # Although we are overriding `inspect.getsourcefile` function, we are NOT trying to resolve source file here!
    # The main purpose of this implementation is to properly resolve relative file names obtained from `co_filename`
    # attribute of code objects (which are, in turn, obtained from in turn are obtained from `frame` and `traceback`
    # objects). PyInstaller strips absolute paths from `co_filename` when collecting modules, as the original absolute
    # paths are not portable/relocatable anyway. The `inspect` module tries to look up the module that corresponds to
    # the code object by comparing modules' `__file__` attribute to the value of `co_filename`. Therefore, our override
    # needs to resolve the relative file names (usually having a .py suffix) into absolute module names (which, in the
    # frozen application, usually have .pyc suffix).
    #
    # The `inspect` module retrieves the actual source code using `linecache.getlines()`. If the passed source filename
    # does not exist, the underlying implementation end up resolving the module, and obtains the source via loader's
    # `get_source` method. So for modules in the PYZ archive, it ends up calling `get_source` implementation on our
    # `PyiFrozenLoader`. For modules in `base_library.zip`, it ends up calling `get_source` on python's own
    # `zipimport.zipimporter`; to properly handle out-of-zip source files, we therefore need to monkey-patch
    # `get_source` with our own override that translates the in-zip .pyc filename into out-of-zip .py file location
    # and loads the source (this override is done in `pyimod02_importers` module).
    #
    # The above-described fallback takes place if the .pyc file does not exist on filesystem - if this ever becomes
    # a problem, we could consider monkey-patching `linecache.updatecache` (and possibly `checkcache`) to translate
    # .pyc paths in `sys._MEIPASS` and `base_library.zip` into .py paths in `sys._MEIPASS` before calling the original
    # implementation.
    _orig_inspect_getsourcefile = inspect.getsourcefile

    def _pyi_getsourcefile(object):
        filename = inspect.getfile(object)
        filename = os.path.normpath(filename)  # Ensure path component separators are normalized.
        if not os.path.isabs(filename):
            # Check if given filename matches the basename of __main__'s __file__.
            main_file = getattr(sys.modules['__main__'], '__file__', None)
            if main_file and filename == os.path.basename(main_file):
                return main_file

            # If filename ends with .py suffix and does not correspond to frozen entry-point script, convert it to
            # corresponding .pyc in `sys._MEIPASS` or `sys._MEIPASS/base_library.zip`.
            if filename.endswith('.py'):
                pyc_filename = filename + 'c'
                prefix = BASE_LIBRARY if pyc_filename in base_library_files else SYS_PREFIX
                return os.path.normpath(os.path.join(prefix, pyc_filename))
        elif filename.startswith(SYS_PREFIX) and filename.endswith('.pyc'):
            # If filename is already PyInstaller-compatible, prevent any further processing (i.e., with original
            # implementation).
            return filename
        # Use original implementation as a fallback.
        return _orig_inspect_getsourcefile(object)

    inspect.getsourcefile = _pyi_getsourcefile


_pyi_rthook()
del _pyi_rthook
