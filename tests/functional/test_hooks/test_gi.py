#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
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

# Names of all "gi.repository" packages provided by PyGObject  to be
# tested below, typically corresponding to those packages hooked by PyInstaller.
gi_repositories = [('Gst', '1.0'), ('GLib', '2.0'), ('GModule', '2.0'),
                   ('GObject', '2.0'), ('GdkPixbuf', '2.0'), ('Gio', '2.0'),
                   ('Clutter', '1.0'), ('GtkClutter', '1.0'),
                   ('Champlain', '0.12'), ('GtkChamplain', '0.12')]
gi_repository_names = [x[0] for x in gi_repositories]

# Names of the same packages, decorated to be skipped if unimportable.
gi_repositories_skipped_if_unimportable = [
    importorskip('gi.repository.' + gi_repository_name)
    ((gi_repository_name, gi_repository_version))
    for gi_repository_name, gi_repository_version in gi_repositories
]


# Test the usability of "gi.repository" packages provided by PyGObject.
@importorskip('gi.repository')
@parametrize(
    ('repository_name', 'version'),
    gi_repositories_skipped_if_unimportable,
    # Ensure human-readable test parameter names.
    ids=gi_repository_names)
def test_gi_repository(pyi_builder, repository_name, version):
    '''
    Test the importability of the `gi.repository` subpackage with the passed
    name installed with PyGObject (e.g., `GLib`, corresponding to the
    `gi.repository.GLib` subpackage). Version '1.0' are for PyGObject >=1.0,
    '2.0' for PyGObject >= 2.0 and some other libraries have strange version
    (eg. Champlain)
    '''

    # Test the importability of this subpackage.
    pyi_builder.test_source('''
        import gi
        gi.require_version('{repository_name}', '{version}')
        from gi.repository import {repository_name}
        print({repository_name})
        '''.format(repository_name=repository_name, version=version))
