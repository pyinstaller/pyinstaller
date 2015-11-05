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
import py_compile

import pytest

from PyInstaller.lib.modulegraph import modulegraph
from PyInstaller.utils.tests import skipif, is_py2, is_py3

def _import_and_get_node(tmpdir, module_name, path=None):
    script = tmpdir.join('script.py')
    script.write('import %s' % module_name)
    if path is None:
        path = [str(tmpdir)]
    mg = modulegraph.ModuleGraph(path)
    mg.run_script(str(script))
    return mg.findNode(module_name)


def test_sourcefile(tmpdir):
    tmpdir.join('source.py').write('###')
    node = _import_and_get_node(tmpdir, 'source')
    assert isinstance(node, modulegraph.SourceModule)


def test_invalid_sourcefile(tmpdir):
    tmpdir.join('invalid_source.py').write('invalid python-source code')
    node = _import_and_get_node(tmpdir, 'invalid_source')
    assert isinstance(node, modulegraph.InvalidSourceModule)


@skipif(is_py3, reason='Python 3 does not look into the __pycache__')
def test_compliedfile(tmpdir):
    pysrc = tmpdir.join('compiled.py')
    pysrc.write('###')
    py_compile.compile(str(pysrc))
    pysrc.remove()
    node = _import_and_get_node(tmpdir, 'compiled')
    assert isinstance(node, modulegraph.CompiledModule)


def test_invalid_compiledfile(tmpdir):
    tmpdir.join('invalid_compiled.pyc').write('invalid byte-code')
    node = _import_and_get_node(tmpdir, 'invalid_compiled')
    assert isinstance(node, modulegraph.InvalidCompiledModule)


def test_builtin(tmpdir):
    node = _import_and_get_node(tmpdir, 'sys', path=sys.path)
    assert isinstance(node, modulegraph.BuiltinModule)


def test_extension(tmpdir):
    node = _import_and_get_node(tmpdir, 'array', path=sys.path)
    assert isinstance(node, modulegraph.Extension)


def test_package(tmpdir):
    node = _import_and_get_node(tmpdir, 'distutils', path=sys.path)
    assert isinstance(node, modulegraph.Package)
    import distutils
    assert distutils.__file__ in (node.filename, node.filename+'c')
    assert node.packagepath == distutils.__path__


@skipif(is_py3, reason='Python 3 does not look into the __pycache__')
def test_compiled_package(tmpdir):
    pysrc = tmpdir.join('stuff', '__init__.py').ensure()
    pysrc.write('###')
    py_compile.compile(str(pysrc))
    pysrc.remove()
    node = _import_and_get_node(tmpdir, 'stuff')
    assert node.__class__ is modulegraph.Package
    assert node.filename == str(pysrc) + 'c'
    assert node.packagepath == [str(pysrc.dirname)]


@skipif(is_py2, reason='Requires Python 3 or newer')
def test_nspackage_pep420(tmpdir):
    p1 = tmpdir.join('p1')
    p2 = tmpdir.join('p2')
    p1.join('stuff', 'a.py').ensure().write('###')
    p2.join('stuff', 'b.py').ensure().write('###')
    path = [str(p1), str(p2)]

    script = tmpdir.join('script.py')
    script.write('import stuff.a, stuff.b')
    mg = modulegraph.ModuleGraph(path)
    mg.run_script(str(script))

    mg.report()

    assert isinstance(mg.findNode('stuff.a'), modulegraph.SourceModule)
    assert isinstance(mg.findNode('stuff.b'), modulegraph.SourceModule)

    node = mg.findNode('stuff')
    assert isinstance(node, modulegraph.NamespacePackage)
    assert node.packagepath == [os.path.join(p, 'stuff') for p in path]

# :todo: test_namespace_setuptools
# :todo: test_namespace_pkg_resources
