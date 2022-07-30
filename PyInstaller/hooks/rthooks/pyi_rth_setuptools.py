#-----------------------------------------------------------------------------
# Copyright (c) 2022, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

# This runtime hook performs the equivalent of the distutils-precedence.pth from the setuptools package;
# it registers a special meta finder that diverts import of distutils to setuptools._distutils, if
# available.
try:
    import os
    if os.environ.get("SETUPTOOLS_USE_DISTUTILS", "local") == "local":
        import _distutils_hack
        _distutils_hack.add_shim()
except Exception:
    pass
