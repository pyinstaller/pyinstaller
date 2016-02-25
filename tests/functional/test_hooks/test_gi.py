#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Functional tests for PyGObject.
"""

from PyInstaller.utils.tests import importorskip, parametrize


## For PyGObject >= 1.0

# Test the usability of "gi.repository" packages provided by PyGObject >= 1.0.
@importorskip('gi.repository.Gst')
def test_gi_gst_binding(pyi_builder):
    pyi_builder.test_source('''
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst
        Gst.init(None)
        print(Gst)
    ''')


## For PyGObject >= 2.0

# Names of all "gi.repository" packages provided by PyGObject >= 2.0 to be
# tested below, typically corresponding to those packages hooked by PyInstaller.
gi2_repository_names = ['GLib', 'GModule', 'GObject', 'GdkPixbuf', 'Gio',]

# Names of the same packages, decorated to be skipped if unimportable.
gi2_repository_names_skipped_if_unimportable = [
    importorskip('gi.repository.' + gi2_repository_name)(gi2_repository_name)
    for gi2_repository_name in gi2_repository_names
]

# Test the usability of "gi.repository" packages provided by PyGObject >= 2.0.
# For simplicity, these tests are parametrized as
# "test_gi2_repository[{one_type}-{repository_name}]" (e.g.,
# "test_gi2_repository[onedir-GdkPixbuf]").
@importorskip('gi.repository')
@parametrize(
    'repository_name',
    gi2_repository_names_skipped_if_unimportable,
    # Ensure human-readable test parameter names.
    ids=gi2_repository_names)
def test_gi2_repository(pyi_builder, repository_name):
    '''
    Test the importability of the `gi.repository` subpackage with the passed
    name installed with PyGObject >= 2.0 (e.g., `GLib`, corresponding to the
    `gi.repository.GLib` subpackage).
    '''

    # Test the importability of this subpackage.
    pyi_builder.test_source('''
        import gi
        gi.require_version('{repository_name}', '2.0')
        from gi.repository import {repository_name}
        print({repository_name})
        '''.format(repository_name=repository_name))
