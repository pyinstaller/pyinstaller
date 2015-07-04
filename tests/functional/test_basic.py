#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import sys

from PyInstaller.utils.tests import importorskip, skipif_winorosx


@skipif_winorosx
def test_absolute_ld_library_path(pyi_builder):
    pyi_builder.test_script('absolute_ld_library_path.py')


def test_absolute_python_path(pyi_builder):
    pyi_builder.test_script('absolute_python_path.py')


def test_celementtree(pyi_builder):
    pyi_builder.test_script('celementtree.py')


@importorskip('codecs')
def test_codecs(pyi_builder):
    pyi_builder.test_script('codecs.py')


def test_decoders_ascii(pyi_builder):
    pyi_builder.test_script('decoders_ascii.py')


def test_email(pyi_builder):
    pyi_builder.test_script('email.py')


def test_filename(pyi_builder):
    pyi_builder.test_script('filename.py')


def test_getfilesystemencoding(pyi_builder):
    pyi_builder.test_script('getfilesystemencoding.py')


def test_helloworld(pyi_builder):
    pyi_builder.test_script('helloworld.py')


def test_module__file__attribute(pyi_builder):
    pyi_builder.test_script('module__file__attribute.py')


def test_module_attributes(tmpdir, pyi_builder):
    # Create file in tmpdir with path to python executable and if it is running
    # in debug mode.
    # Test script uses python interpreter to compare module attributes.
    with open(os.path.join(tmpdir.strpath, 'python_exe.build'), 'w') as f:
        f.write(sys.executable + "\n")
        f.write('debug=%s' % __debug__ + '\n')
        # On Windows we need to preserve systme PATH for subprocesses in tests.
        f.write(os.environ.get('PATH') + '\n')
    pyi_builder.test_script('module_attributes.py')


def test_module_reload(pyi_builder):
    pyi_builder.test_script('module_reload.py')


@importorskip('multiprocess')
def test_multiprocess(pyi_builder):
    pyi_builder.test_script('multiprocess.py')


def test_(pyi_builder):
    pyi_builder.test_script('')


def test_(pyi_builder):
    pyi_builder.test_script('')


def test_(pyi_builder):
    pyi_builder.test_script('')


def test_(pyi_builder):
    pyi_builder.test_script('')


def test_(pyi_builder):
    pyi_builder.test_script('')


def test_(pyi_builder):
    pyi_builder.test_script('')


def test_(pyi_builder):
    pyi_builder.test_script('')


def test_(pyi_builder):
    pyi_builder.test_script('')


def test_(pyi_builder):
    pyi_builder.test_script('')
