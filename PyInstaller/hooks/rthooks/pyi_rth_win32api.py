#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

# Starting with Python 3.8, win32api failed with "ImportError: DLL load failed while importing win32clipboard: The
# specified module could not be found." This seems to be caused by pywintypes.dll not being found in various situations.
# See https://github.com/mhammond/pywin32/pull/1430 and
# https://github.com/mhammond/pywin32/commit/71afa71e11e6631be611ca5cb57cda526
# As a work-around, import pywintypes prior to win32api.

import pywintypes  # noqa: F401
