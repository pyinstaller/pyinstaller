#-----------------------------------------------------------------------------
# Copyright (c) 2005-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import ast
import os
import os.path
import sys
import py_compile
import textwrap
import zipfile

import pytest

from PyInstaller.lib.modulegraph import modulegraph
from PyInstaller.utils.tests import xfail, skipif, skipif_win, is_py2, is_py3

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
    node = _import_and_get_node(tmpdir, '_ctypes', path=sys.path)
    assert isinstance(node, modulegraph.Extension)


def test_package(tmpdir):
    pysrc = tmpdir.join('stuff', '__init__.py')
    pysrc.write('###', ensure=True)
    node = _import_and_get_node(tmpdir, 'stuff')
    assert node.__class__ is modulegraph.Package
    assert node.filename in (str(pysrc), str(pysrc)+'c')
    assert node.packagepath == [pysrc.dirname]


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

#-- Tests with a single module in a zip-file

def _zip_directory(filename, path):
    with zipfile.ZipFile(filename, mode='w') as zfh:
        for filename in path.visit(fil='*.py*'):
            zfh.write(str(filename), filename.relto(path))


def test_zipped_module_source(tmpdir):
    pysrc = tmpdir.join('stuff.py')
    pysrc.write('###', ensure=True)
    zipfilename = str(tmpdir.join('unstuff.zip'))
    _zip_directory(zipfilename, tmpdir)
    node = _import_and_get_node(tmpdir, 'stuff', path=[zipfilename])
    assert node.__class__ is modulegraph.SourceModule
    assert node.filename.startswith(os.path.join(zipfilename, 'stuff.py'))


def test_zipped_module_source_and_compiled(tmpdir):
    pysrc = tmpdir.join('stuff.py')
    pysrc.write('###', ensure=True)
    py_compile.compile(str(pysrc))
    zipfilename = str(tmpdir.join('unstuff.zip'))
    _zip_directory(zipfilename, tmpdir)
    node = _import_and_get_node(tmpdir, 'stuff', path=[zipfilename])
    # Do not care whether it's source or compiled, as long as it is
    # neither invalid nor missing.
    assert node.__class__ in (modulegraph.SourceModule, modulegraph.CompiledModule)
    assert node.filename.startswith(os.path.join(zipfilename, 'stuff.py'))


@skipif(is_py3, reason='Python 3 does not look into the __pycache__')
def test_zipped_module_compiled(tmpdir):
    pysrc = tmpdir.join('stuff.py')
    pysrc.write('###', ensure=True)
    py_compile.compile(str(pysrc))
    pysrc.remove()
    zipfilename = str(tmpdir.join('unstuff.zip'))
    _zip_directory(zipfilename, tmpdir)
    node = _import_and_get_node(tmpdir, 'stuff', path=[zipfilename])
    assert node.__class__ is modulegraph.CompiledModule
    assert node.filename.startswith(os.path.join(zipfilename, 'stuff.py'))


#-- Tests with a package in a zip-file

def _zip_package(filename, path):
    with zipfile.ZipFile(filename, mode='w') as zfh:
        for filename in path.visit():
            zfh.write(str(filename), filename.relto(path.dirname))

def test_zipped_package_source(tmpdir):
    pysrc = tmpdir.join('stuff', '__init__.py')
    pysrc.write('###', ensure=True)
    zipfilename = str(tmpdir.join('stuff.zip'))
    _zip_package(zipfilename, tmpdir.join('stuff'))
    node = _import_and_get_node(tmpdir, 'stuff', path=[zipfilename])
    assert node.__class__ is modulegraph.Package
    assert node.packagepath == [os.path.join(zipfilename, 'stuff')]


def test_zipped_package_source_and_compiled(tmpdir):
    pysrc = tmpdir.join('stuff', '__init__.py')
    pysrc.write('###', ensure=True)
    py_compile.compile(str(pysrc))
    zipfilename = str(tmpdir.join('stuff.zip'))
    _zip_package(zipfilename, tmpdir.join('stuff'))
    node = _import_and_get_node(tmpdir, 'stuff', path=[zipfilename])
    assert node.__class__ is modulegraph.Package
    assert node.packagepath == [os.path.join(zipfilename, 'stuff')]


@skipif(is_py3, reason='Python 3 does not look into the __pycache__')
def test_zipped_package_compiled(tmpdir):
    pysrc = tmpdir.join('stuff', '__init__.py')
    pysrc.write('###', ensure=True)
    py_compile.compile(str(pysrc))
    pysrc.remove()
    zipfilename = str(tmpdir.join('stuff.zip'))
    _zip_package(zipfilename, tmpdir.join('stuff'))
    node = _import_and_get_node(tmpdir, 'stuff', path=[zipfilename])
    assert node.__class__ is modulegraph.Package
    assert node.packagepath == [os.path.join(zipfilename, 'stuff')]


#-- Namespace packages

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

@skipif_win
def test_symlinks(tmpdir):
    base_dir = tmpdir.join('base').ensure(dir=True)
    p1_init = tmpdir.join('p1', '__init__.py').ensure()
    p2_init = tmpdir.join('p2', '__init__.py').ensure()
    p1_init.write('###')
    p2_init.write('###')

    base_dir.join('p1').ensure(dir=True)

    os.symlink(str(p1_init), str(base_dir.join('p1', '__init__.py')))
    os.symlink(str(p2_init), str(base_dir.join('p1', 'p2.py')))

    node = _import_and_get_node(base_dir, 'p1.p2')
    assert isinstance(node, modulegraph.SourceModule)


@xfail(reason="FIXME: modulegraph does not use correct order")
def test_import_order_1(tmpdir):
    # Ensure modulegraph processes modules in the same order as Python does.

    class MyModuleGraph(modulegraph.ModuleGraph):
        def _load_module(self, fqname, fp, pathname, info):
            if not record or record[-1] != fqname:
                record.append(fqname) # record non-consecutive entries
            return super(MyModuleGraph, self)._load_module(fqname, fp,
                                                           pathname, info)

    record = []

    for filename, content in (
        ('a/',     ' from . import c, d'),
        ('a/c',            '#'),
        ('a/d/',    'from . import f, g, h'),
        ('a/d/f/',  'from . import j, k'),
        ('a/d/f/j',         '#'),
        ('a/d/f/k',         '#'),
        ('a/d/g/',   'from . import l, m'),
        ('a/d/g/l',         '#'),
        ('a/d/g/m',         '#'),
        ('a/d/h',           '#'),
        ('b/',      'from . import e'),
        ('b/e/',    'from . import i'),
        ('b/e/i',           '#')):
        if filename.endswith('/'): filename += '__init__'
        tmpdir.join(*(filename+'.py').split('/')).ensure().write(content)

    script = tmpdir.join('script.py')
    script.write('import a, b')
    mg = MyModuleGraph([str(tmpdir)])
    mg.run_script(str(script))

    # This is the order Python imports these modules given that script.
    expected = ['a',
                    'a.c', 'a.d', 'a.d.f', 'a.d.f.j', 'a.d.f.k',
                    'a.d.g', 'a.d.g.l', 'a.d.g.m',
                    'a.d.h',
               'b', 'b.e', 'b.e.i']
    assert record == expected


def test_import_order_2(tmpdir):
    # Ensure modulegraph processes modules in the same order as Python does.

    class MyModuleGraph(modulegraph.ModuleGraph):
        def _load_module(self, fqname, fp, pathname, info):
            if not record or record[-1] != fqname:
                record.append(fqname) # record non-consecutive entries
            return super(MyModuleGraph, self)._load_module(fqname, fp,
                                                           pathname, info)

    record = []

    for filename, content in (
        ('a/',      '#'),
        ('a/c/',    '#'),
        ('a/c/g',   '#'),
        ('a/c/h',   'from . import g'),
        ('a/d/',    '#'),
        ('a/d/i',   'from ..c import h'),
        ('a/d/j/',  'from .. import i'),
        ('a/d/j/o', '#'),
        ('b/',      'from .e import k'),
        ('b/e/',    'import a.c.g'),
        ('b/e/k',   'from .. import f'),
        ('b/e/l',   'import a.d.j'),
        ('b/f/',    '#'),
        ('b/f/m',   '#'),
        ('b/f/n/',  '#'),
        ('b/f/n/p', 'from ...e import l')):
        if filename.endswith('/'): filename += '__init__'
        tmpdir.join(*(filename+'.py').split('/')).ensure().write(content)

    script = tmpdir.join('script.py')
    script.write('import b.f.n.p')
    mg = MyModuleGraph([str(tmpdir)])
    mg.run_script(str(script))

    # This is the order Python imports these modules given that script.
    expected = ['b', 'b.e',
                'a', 'a.c', 'a.c.g',
                'b.e.k',
                'b.f', 'b.f.n', 'b.f.n.p',
                'b.e.l',
                'a.d', 'a.d.j', 'a.d.i', 'a.c.h']
    assert record == expected
    print(record)


#---- scan bytecode

def __scan_code(code, use_ast, monkeypatch):
    mg = modulegraph.ModuleGraph()
    # _process_imports would set _deferred_imports to None
    monkeypatch.setattr(mg, '_process_imports', lambda m: None)
    module = mg.createNode(modulegraph.Script, 'dummy.py')

    code = textwrap.dedent(code)
    if use_ast:
        co_ast = compile(code, 'dummy', 'exec', ast.PyCF_ONLY_AST)
        co = compile(co_ast, 'dummy', 'exec')
    else:
        co_ast = None
        co = compile(code, 'dummy', 'exec')
    mg._scan_code(module, co)
    return module


@pytest.mark.parametrize("use_ast", (True, False))
def test_scan_code__empty(monkeypatch, use_ast):
    code = "# empty code"
    module = __scan_code(code, use_ast, monkeypatch)
    assert len(module._deferred_imports) == 0
    assert len(module._global_attr_names) == 0


@pytest.mark.parametrize("use_ast", (True, False))
def test_scan_code__basic(monkeypatch, use_ast):
    code = """
    import os.path
    from sys import maxint, exitfunc, platform
    del exitfunc
    def testfunc():
        import shutil
    """
    module = __scan_code(code, use_ast, monkeypatch)
    assert len(module._deferred_imports) == 3
    assert ([di[1][0] for di in module._deferred_imports]
            == ['os.path', 'sys', 'shutil'])
    assert module.is_global_attr('maxint')
    assert module.is_global_attr('os')
    assert module.is_global_attr('platform')
    assert not module.is_global_attr('shutil') # not imported at module level
    assert not module.is_global_attr('exitfunc')
