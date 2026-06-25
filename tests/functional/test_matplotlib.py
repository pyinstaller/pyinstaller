#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Functional tests for Matplotlib.
"""

import json
import sys

import pytest

from PyInstaller import isolated
from PyInstaller.utils.tests import importorskip, onedir_only
from PyInstaller.utils.hooks import check_requirement

# List of tuples "(backend_name, qt_bindings)", where:
#
# * "backend_name" is the name of a Matplotlib backend to be tested below.
# * "qt_bindings" is the name of the external Qt bindings package required by this backend.
#
if check_requirement("matplotlib >= 3.5.0"):
    # Matplotlib 3.5.0 introduced a unified Qt backend that supports PySide2, PyQt5, PySide6, and PyQt6.
    _backends = [
        ('QtAgg', 'PyQt5'),
        ('QtAgg', 'PySide2'),
        ('QtAgg', 'PyQt6'),
        ('QtAgg', 'PySide6'),
    ]
else:
    _backends = [
        ('Qt5Agg', 'PyQt5'),
        ('Qt5Agg', 'PySide2'),
    ]


# Test Matplotlib with access to only one backend at a time.
@importorskip('matplotlib')
@pytest.mark.parametrize(
    'backend_name, qt_bindings',
    [
        pytest.param(backend_name, qt_bindings, marks=importorskip(qt_bindings))
        for backend_name, qt_bindings in _backends
    ],
    ids=[qt_bindings for backend_name, qt_bindings in _backends],
)
def test_matplotlib(pyi_builder, monkeypatch, backend_name, qt_bindings):
    '''
    Test Matplotlib with the passed backend enabled, the passed backend package included with this frozen application,
    all other backend packages explicitly excluded from this frozen application, and the passed rcParam key set to the
    corresponding passed value if that key is _not_ `None` or ignore that value otherwise.
    '''

    # Exclude all Qt bindings except the ones we are using in this test.
    pyi_args = [
        f'--exclude-module={bindings_name}' for backend_name, bindings_name in _backends if bindings_name != qt_bindings
    ]

    # Test program
    pyi_builder.test_source(
        f"""
        import os
        import sys
        import tempfile

        import matplotlib

        # Matplotlib >= v3.4.0 allows Qt bindings name in QT_API environment variable to be capitalized. Lower-case it
        # here just in case we ever happen to run the test with older version.
        qt_bindings_lower = {qt_bindings!r}.lower()

        # Report these parameters.
        print(f'Testing Matplotlib with backend={backend_name} and QT_API={{qt_bindings_lower}}')

        # Configure Matplotlib *BEFORE* calling any Matplotlib functions.
        matplotlib.rcParams['backend'] = {backend_name!r}
        os.environ['QT_API'] = qt_bindings_lower

        # Enable the desired backend *BEFORE* plotting with this backend.
        matplotlib.use({backend_name!r})

        # A runtime hook should force Matplotlib to create its configuration directory in a temporary directory
        # rather than in $HOME/.matplotlib.
        configdir = os.environ['MPLCONFIGDIR']
        print(f'MPLCONFIGDIR: {{configdir}}')
        if not configdir.startswith(tempfile.gettempdir()):
            raise SystemExit('MPLCONFIGDIR not pointing to temp directory.')

        # Test access to the standard 'mpl_toolkits' namespace package installed with Matplotlib.
        # Note that this import was reported to fail under Matplotlib 1.3.0.
        from mpl_toolkits import axes_grid1

        # Try importing pyplot. This will attempt to activate the selected backend.
        from matplotlib import pyplot as plt
        """,
        pyi_args=pyi_args,
    )


# Check that "all backends" collection mode in fact collects all available backends.
@importorskip('matplotlib')
@onedir_only
def test_matplotlib_all_backends(pyi_builder, monkeypatch, tmp_path):
    # Patch Analysis to set backend collection mode via hooksconfig
    import PyInstaller.building.build_main

    class _Analysis(PyInstaller.building.build_main.Analysis):
        def __init__(self, *args, **kwargs):
            kwargs['hooksconfig'] = {
                "matplotlib": {
                    "backends": "all",
                }
            }
            super().__init__(*args, **kwargs)

    monkeypatch.setattr('PyInstaller.building.build_main.Analysis', _Analysis)

    # Test program; retrieve backends in frozen matplotlib
    result_file = tmp_path / 'results.txt'
    pyi_builder.test_source(
        """
        import sys
        import json
        import importlib.util

        import matplotlib

        backends = matplotlib.rcsetup.all_backends

        def _backend_module_name(name):
            if name.startswith("module://"):
                return name[9:]
            return f"matplotlib.backends.backend_{name.lower()}"

        backend_info = []
        for backend in backends:
            backend_module = _backend_module_name(backend)

            # Check that module is available (but not that it is actually importable)
            spec = importlib.util.find_spec(backend_module)
            exists = spec is not None

            backend_info.append((backend, backend_module, exists))

        print("Matplotlib backends:", file=sys.stderr)
        for name, module, exists in backend_info:
            print(f"  name={name}, module={module}, exists={exists}", file=sys.stderr)

        if len(sys.argv) > 1:
            with open(sys.argv[1], "w") as fp:
                json.dump(backend_info, fp)
        """,
        app_args=[str(result_file)],
    )

    with open(result_file, "r", encoding="utf-8") as fp:
        frozen_backends_info = json.load(fp)

    frozen_backends_info = sorted(frozen_backends_info)
    print("Backends in frozen matplotlib:", file=sys.stderr)
    for name, module, exists in frozen_backends_info:
        print(f"  name={name}, module={module}, exists={exists}", file=sys.stderr)

    # Importable backends in unfrozen matplotlib
    @isolated.decorate
    def _get_unfrozen_backends():
        import importlib

        import matplotlib

        backends = matplotlib.rcsetup.all_backends

        def _backend_module_name(name):
            if name.startswith("module://"):
                return name[9:]
            return f"matplotlib.backends.backend_{name.lower()}"

        backend_info = []
        for backend in backends:
            backend_module = _backend_module_name(backend)

            try:
                importlib.import_module(backend_module)
                importable = True
            except Exception:
                importable = False

            backend_info.append([backend, backend_module, importable])

        return backend_info

    unfrozen_backends_info = sorted(_get_unfrozen_backends())
    print("Importable backends in unfrozen matplotlib:", file=sys.stderr)
    for name, module, importable in unfrozen_backends_info:
        print(f"  name={name}, module={module}, importable={importable}", file=sys.stderr)

    # The available backends in frozen matplotlib should be the ones that are importable in unfrozen matplotlib.
    assert frozen_backends_info == unfrozen_backends_info
