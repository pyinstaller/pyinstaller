#-----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

# Historically, matplotlib stored absolute paths to font files in its on-disk font cache. For frozen onefile
# applications, those paths pointed into the `_MEIxxxxx` extraction directory, which changes on every run; the next
# run would then fail to open the cached font files with errors such as:
#
#     RuntimeError: Could not open facefile
#
# As a workaround, this run-time hook forced matplotlib to use a fresh, temporary config directory (via the
# `MPLCONFIGDIR` environment variable) on every launch, rebuilding the font cache from scratch.
#
# Since matplotlib 3.0, font-cache entries are stored as paths relative to matplotlib's data directory, so the
# stale-path problem no longer exists. Keeping the workaround on modern matplotlib is actively harmful, because
# pointing `MPLCONFIGDIR` at a fresh empty directory on every launch forces matplotlib to rebuild its font cache
# every single time the frozen app starts, which noticeably slows startup.
#
# Therefore, this hook now applies the workaround only for matplotlib < 3.0. For matplotlib >= 3.0, we leave
# `MPLCONFIGDIR` alone, so matplotlib uses its default persistent user cache directory.


def _pyi_rthook():
    # Determine the installed matplotlib version without importing matplotlib itself (importing matplotlib is
    # expensive and has side effects we would rather avoid in a run-time hook that might end up being a no-op).
    use_legacy_workaround = True
    try:
        from importlib.metadata import version as _pkg_version

        _mpl_version = _pkg_version("matplotlib")
        # Parse the leading numeric components (major[, minor, ...]). We only care about the major version.
        _major_str = _mpl_version.split('.', 1)[0]
        # Strip any non-digit suffix (e.g. dev/rc markers that might sneak into the first component).
        _major_digits = ''.join(ch for ch in _major_str if ch.isdigit())
        if _major_digits and int(_major_digits) >= 3:
            use_legacy_workaround = False
    except Exception:
        # If we cannot determine the version for any reason, fall through to the legacy workaround. It is safer
        # to pay the font-cache-rebuild cost than to risk broken font loading on an old matplotlib.
        pass

    if not use_legacy_workaround:
        return

    import atexit
    import os
    import shutil

    import _pyi_rth_utils.tempfile  # PyInstaller's run-time hook utilities module

    # Isolate matplotlib's config dir into temporary directory.
    # Use our replacement for `tempfile.mkdtemp` function that properly restricts access to directory on all platforms.
    configdir = _pyi_rth_utils.tempfile.secure_mkdtemp()
    os.environ['MPLCONFIGDIR'] = configdir

    try:
        # Remove temp directory at application exit and ignore any errors.
        atexit.register(shutil.rmtree, configdir, ignore_errors=True)
    except OSError:
        pass


_pyi_rthook()
del _pyi_rthook
