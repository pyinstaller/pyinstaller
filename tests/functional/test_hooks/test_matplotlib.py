#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Functional tests for Matplotlib.
"""

import pytest
from PyInstaller.utils.tests import importorskip


# List of 4-tuples "(backend_name, package_name, rcParams_key, rcParams_value)",
# where:
#
# * "backend_name" is the name of a Matplotlib backend to be tested below.
# * "package_name" is the name of the external package required by this backend.
# * "rcParams_key" is the name of a Matplotlib parameter to be set before testing
#   this backend or "None" if no parameter is to be set.
# * "rcParams_value" is the value to set that parameter to if "rcParams_key" is
#   not "None" or ignored otherwise.
backend_rcParams_key_values = [
    # PySide.
    ('Qt4Agg', 'PySide', 'backend.qt4', 'PySide'),
    # PyQt4.
    ('Qt4Agg', 'PyQt4', 'backend.qt4', 'PyQt4'),
    # PyQt5.
    ('Qt5Agg', 'PyQt5', 'backend.qt5', 'PyQt5'),
]

# Same list, decorated to skip all backends whose packages are unimportable.
backend_rcParams_key_values_skipped_if_unimportable = [
    importorskip(backend_rcParams_key_value[1])(backend_rcParams_key_value)
    for backend_rcParams_key_value in backend_rcParams_key_values
]

# Names of all packages required by backends listed above.
package_names = [
    backend_rcParams_key_value[1]
    for backend_rcParams_key_value in backend_rcParams_key_values
]

# Test Matplotlib with access to only one backend at a time.
@importorskip('matplotlib')
@pytest.mark.parametrize(
    'backend_name, package_name, rcParams_key, rcParams_value',
    backend_rcParams_key_values_skipped_if_unimportable,
    ids=package_names)
def test_matplotlib(
    pyi_builder, backend_name, package_name, rcParams_key, rcParams_value):
    '''
    Test Matplotlib with the passed backend enabled, the passed backend package
    included with this frozen application, all other backend packages explicitly
    excluded from this frozen application, and the passed rcParam key set to the
    corresponding passed value if that key is _not_ `None` or ignore that value
    otherwise.
    '''

    # PyInstaller options excluding all backend packages except the passed
    # backend package. This is especially critical for Qt backend packages
    # (e.g., "PyQt4", "PySide"). On first importation, Matplotlib attempts to
    # import all available Qt packages. However, runtime PyInstaller hooks fail
    # when multiple Qt packages are frozen into the same application. For each
    # such package, all other Qt packages must be excluded.
    pyi_args = [
        '--exclude-module=' + package_name_excludable
        for package_name_excludable in package_names
        if  package_name_excludable != package_name
    ]

    # Script to be tested, enabling this Qt backend.
    test_script = ('''
    import matplotlib, os, sys, tempfile

    # Localize test parameters.
    backend_name = {backend_name!r}
    rcParams_key = {rcParams_key!r}
    rcParams_value = {rcParams_value!r}

    # Report these parameters.
    print('Testing Matplotlib with:\\n'
        '\\tbackend: {{}}\\n'
        '\\trcParams:\\n'
        '\\t\\tkey: {{}}\\n'
        '\\t\\tvalue: {{}}'.format(
        backend_name, rcParams_key, rcParams_value))

    # Configure Matplotlib *BEFORE* calling any Matplotlib functions.
    matplotlib.rcParams[rcParams_key] = rcParams_value

    # Enable the desired backend *BEFORE* plotting with this backend.
    matplotlib.use(backend_name)

    # A runtime hook should force Matplotlib to create its configuration
    # directory in a temporary directory rather than in "$HOME/.matplotlib".
    configdir = os.environ['MPLCONFIGDIR']
    print('MPLCONFIGDIR: %s' % configdir)
    if not configdir.startswith(tempfile.gettempdir()):
        raise SystemExit('MPLCONFIGDIR not pointing to temp directory.')

    # Matplotlib's data directory should point to sys._MEIPASS.
    datadir = os.environ['MATPLOTLIBDATA']
    print('MATPLOTLIBDATA: %s' % datadir)
    if not datadir.startswith(sys._MEIPASS):
        raise SystemExit('MATPLOTLIBDATA not pointing to sys._MEIPASS.')

    # Test access to the standard "mpl_toolkits" namespace package installed
    # with Matplotlib. Note that this import was reported to fail under
    # Matplotlib 1.3.0.
    from mpl_toolkits import axes_grid1
    '''.format(
        backend_name=backend_name,
        rcParams_key=rcParams_key,
        rcParams_value=rcParams_value,
    ))

    # Test this script.
    pyi_builder.test_source(test_script, pyi_args=pyi_args)
