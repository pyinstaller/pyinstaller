# -----------------------------------------------------------------------------
# Copyright (c) 2023, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
# -----------------------------------------------------------------------------

import sys
import os

# A boolean indicating whether the frozen application is a macOS .app bundle.
is_macos_app_bundle = sys.platform == 'darwin' and sys._MEIPASS.endswith("Contents/Frameworks")


def prepend_path_to_environment_variable(path, variable_name):
    """
    Prepend the given path to the list of paths stored in the given environment variable (separated by `os.pathsep`).
    If the given path is already specified in the environment variable, no changes are made. If the environment variable
    is not set or is empty, it is set/overwritten with the given path.
    """
    stored_paths = os.environ.get(variable_name)
    if stored_paths:
        # If path is already included, make this a no-op.
        if path in stored_paths:
            return
        # Otherwise, prepend the path
        stored_paths = path + os.pathsep + stored_paths
    else:
        stored_paths = path
    os.environ[variable_name] = stored_paths
