#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import ast
import os
import os.path
import sys
import py_compile
import textwrap
import zipfile
from importlib.machinery import EXTENSION_SUFFIXES

import pytest

from PyInstaller.lib.modulegraph import modulegraph
from PyInstaller.utils.tests import xfail


def _import_and_get_node(tmpdir, module_name, path=None):
    script = tmpdir.join('script.py')
    script.write('import %s' % module_name)
    if path is None:
        path = [str(tmpdir)]
    mg = modulegraph.ModuleGraph(path)
    mg.add_script(str(script))
    return mg.find_node(module_name)


def test_sourcefile(tmpdir):
    tmpdir.join('source.py').write('###')
    node = _import_and_get_node(tmpdir, 'source')
    assert isinstance(node, modulegraph.SourceModule)


def test_invalid_sourcefile(tmpdir):
    tmpdir.join('invalid_source.py').write('invalid python-source code')
    node = _import_and_get_node(tmpdir, 'invalid_source')
    assert isinstance(node, modulegraph.InvalidSourceModule)


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
    assert node.filename in (str(pysrc), str(pysrc) + 'c')
    assert node.packagepath == [pysrc.dirname]


#-- Extension modules


@pytest.mark.parametrize(
    "num, modname, expected_nodetype",
    (
        # package's __init__ module is an extension
        (1, "myextpkg", modulegraph.ExtensionPackage),
        # __init__.py beside the __init__ module being an extension
        (2, "myextpkg", modulegraph.ExtensionPackage),
        # Importing a module beside
        (3, "myextpkg.other", modulegraph.Extension),
        # sub-package's __init__ module is an extension
        (4, "myextpkg.subpkg", modulegraph.ExtensionPackage),
        # importing a module beside, but from a sub-package
        (5, "myextpkg.subpkg.other", modulegraph.Extension),
    )
)
def test_package_init_is_extension(tmpdir, num, modname, expected_nodetype):
    # Regression: Recursion to deep

    def wt(*args):
        f = tmpdir.join(*args)
        f.write_text('###', encoding="ascii")
        return f

    def create_package_files(test_case):
        (tmpdir / 'myextpkg' / 'subpkg').ensure(dir=True)
        m = wt('myextpkg', '__init__' + EXTENSION_SUFFIXES[0])
        if test_case == 1:
            return m
        wt('myextpkg', '__init__.py')
        if test_case == 2:
            return m  # return extension module anway
        m = wt('myextpkg', 'other.py')
        m = wt('myextpkg', 'other' + EXTENSION_SUFFIXES[0])
        if test_case == 3:
            return m
        m = wt('myextpkg', 'subpkg', '__init__.py')
        m = wt('myextpkg', 'subpkg', '__init__' + EXTENSION_SUFFIXES[0])
        if test_case == 4:
            return m
        m = wt('myextpkg', 'subpkg', 'other.py')
        m = wt('myextpkg', 'subpkg', 'other' + EXTENSION_SUFFIXES[0])
        return m

    module_file = create_package_files(num)
    node = _import_and_get_node(tmpdir, modname)
    assert node.__class__ is expected_nodetype
    if expected_nodetype is modulegraph.ExtensionPackage:
        assert node.packagepath == [module_file.dirname]
    else:
        assert node.packagepath is None  # not a package
    assert node.filename == str(module_file)


#-- Basic tests - these seem to be missing in the original modulegraph test-suite


def test_relative_import_missing(tmpdir):
    libdir = tmpdir.join('lib')
    path = [str(libdir)]
    pkg = libdir.join('pkg')
    pkg.join('__init__.py').ensure().write('#')
    pkg.join('x', '__init__.py').ensure().write('#')
    pkg.join('x', 'y', '__init__.py').ensure().write('#')
    pkg.join('x', 'y', 'z.py').ensure().write('from . import DoesNotExist')

    script = tmpdir.join('script.py')
    script.write('import pkg.x.y.z')
    mg = modulegraph.ModuleGraph(path)
    mg.add_script(str(script))
    assert isinstance(mg.find_node('pkg.x.y.z'), modulegraph.SourceModule)
    assert isinstance(mg.find_node('pkg.x.y.DoesNotExist'), modulegraph.MissingModule)


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
    # Do not care whether it is source or compiled, as long as it is neither invalid nor missing.
    assert node.__class__ in (modulegraph.SourceModule, modulegraph.CompiledModule)
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


#-- Namespace packages


def test_nspackage_pep420(tmpdir):
    p1 = tmpdir.join('p1')
    p2 = tmpdir.join('p2')
    p1.join('stuff', 'a.py').ensure().write('###')
    p2.join('stuff', 'b.py').ensure().write('###')
    path = [str(p1), str(p2)]

    script = tmpdir.join('script.py')
    script.write('import stuff.a, stuff.b')
    mg = modulegraph.ModuleGraph(path)
    mg.add_script(str(script))

    mg.report()

    assert isinstance(mg.find_node('stuff.a'), modulegraph.SourceModule)
    assert isinstance(mg.find_node('stuff.b'), modulegraph.SourceModule)

    node = mg.find_node('stuff')
    assert isinstance(node, modulegraph.NamespacePackage)
    assert node.packagepath == [os.path.join(p, 'stuff') for p in path]


# :todo: test_namespace_setuptools
# :todo: test_namespace_pkg_resources


@pytest.mark.darwin
@pytest.mark.linux
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


def test_import_order_1(tmpdir):
    # Ensure modulegraph processes modules in the same order as Python does.

    class MyModuleGraph(modulegraph.ModuleGraph):
        def _load_module(self, fqname, pathname, loader):
            if not record or record[-1] != fqname:
                record.append(fqname)  # record non-consecutive entries
            return super()._load_module(fqname, pathname, loader)

    record = []

    for filename, content in (
        ('a/', 'from . import c, d'),
        ('a/c', '#'),
        ('a/d/', 'from . import f, g, h'),
        ('a/d/f/', 'from . import j, k'),
        ('a/d/f/j', '#'),
        ('a/d/f/k', '#'),
        ('a/d/g/', 'from . import l, m'),
        ('a/d/g/l', '#'),
        ('a/d/g/m', '#'),
        ('a/d/h', '#'),
        ('b/', 'from . import e'),
        ('b/e/', 'from . import i'),
        ('b/e/i', '#'),
    ):
        if filename.endswith('/'):
            filename += '__init__'
        tmpdir.join(*(filename + '.py').split('/')).ensure().write(content)

    script = tmpdir.join('script.py')
    script.write('import a, b')
    mg = MyModuleGraph([str(tmpdir)])
    mg.add_script(str(script))

    # This is the order Python imports these modules given that script.
    expected = [
        'a', 'a.c', 'a.d', 'a.d.f', 'a.d.f.j', 'a.d.f.k', 'a.d.g', 'a.d.g.l', 'a.d.g.m', 'a.d.h', 'b', 'b.e', 'b.e.i'
    ]
    assert record == expected


def test_import_order_2(tmpdir):
    # Ensure modulegraph processes modules in the same order as Python does.

    class MyModuleGraph(modulegraph.ModuleGraph):
        def _load_module(self, fqname, pathname, loader):
            if not record or record[-1] != fqname:
                record.append(fqname)  # record non-consecutive entries
            return super()._load_module(fqname, pathname, loader)

    record = []

    for filename, content in (
        ('a/', '#'),
        ('a/c/', '#'),
        ('a/c/g', '#'),
        ('a/c/h', 'from . import g'),
        ('a/d/', '#'),
        ('a/d/i', 'from ..c import h'),
        ('a/d/j/', 'from .. import i'),
        ('a/d/j/o', '#'),
        ('b/', 'from .e import k'),
        ('b/e/', 'import a.c.g'),
        ('b/e/k', 'from .. import f'),
        ('b/e/l', 'import a.d.j'),
        ('b/f/', '#'),
        ('b/f/m', '#'),
        ('b/f/n/', '#'),
        ('b/f/n/p', 'from ...e import l'),
    ):
        if filename.endswith('/'):
            filename += '__init__'
        tmpdir.join(*(filename + '.py').split('/')).ensure().write(content)

    script = tmpdir.join('script.py')
    script.write('import b.f.n.p')
    mg = MyModuleGraph([str(tmpdir)])
    mg.add_script(str(script))

    # This is the order Python imports these modules given that script.
    expected = [
        'b', 'b.e', 'a', 'a.c', 'a.c.g', 'b.e.k', 'b.f', 'b.f.n', 'b.f.n.p', 'b.e.l', 'a.d', 'a.d.j', 'a.d.i', 'a.c.h'
    ]
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
    assert ([di[1][0] for di in module._deferred_imports] == ['os.path', 'sys', 'shutil'])
    assert module.is_global_attr('maxint')
    assert module.is_global_attr('os')
    assert module.is_global_attr('platform')
    assert not module.is_global_attr('shutil')  # not imported at module level
    assert not module.is_global_attr('exitfunc')


#-- SWIG packages - pyinstaller specific tests


def test_swig_import_simple_BUGGY(tmpdir):
    libdir = tmpdir.join('lib')
    path = [str(libdir)]
    osgeo = libdir.join('pyi_test_osgeo')
    osgeo.join('__init__.py').ensure().write('#')
    osgeo.join('pyi_gdal.py').write('# automatically generated by SWIG\n' 'import _pyi_gdal')
    osgeo.join('_pyi_gdal.py').write('#')

    script = tmpdir.join('script.py')
    script.write('from pyi_test_osgeo import pyi_gdal')
    mg = modulegraph.ModuleGraph(path)
    mg.add_script(str(script))

    assert isinstance(mg.find_node('pyi_test_osgeo'), modulegraph.Package)
    assert isinstance(mg.find_node('pyi_test_osgeo.pyi_gdal'), modulegraph.SourceModule)
    # The "C" module is frozen under its unqualified rather than qualified name.
    # See comment in modulegraph._safe_import_hook.
    # BUG: modulegraph contains a probable bug: Only the module's identifier is changed, not the module's graphident.
    # Thus the node is still found under its old name. The relevant code was brought from PyInstaller to upstream,
    # so this might be PyInstaller's fault. See test_swig_import_simple for what it should be.
    # This is a separate test-case, not marked as xfail, so we can spot whether the SWIG support works at all.
    assert isinstance(mg.find_node('pyi_test_osgeo._pyi_gdal'), modulegraph.SourceModule)
    # Due the the buggy implementation, the graphident is unchanged, but at least the identifier should have changed.
    assert mg.find_node('pyi_test_osgeo._pyi_gdal').identifier == '_pyi_gdal'
    # Due the the buggy implementation, this node does not exist.
    assert mg.find_node('_pyi_gdal') is None
    return mg  # for use in test_swig_import_simple_BUG


@xfail
def test_swig_import_simple(tmpdir):
    # Test the expected (but not implemented) behavior if SWIG support.
    mg = test_swig_import_simple_BUGGY(tmpdir)
    # Given the bug in modulegraph (see test_swig_import_simple_BUGGY) this is what would be the expected behavior.
    # TODO: When modulegraph is fixed, merge the two test-cases and correct test_swig_import_from_top_level
    # and siblings.
    assert mg.find_node('pyi_test_osgeo._pyi_gdal') is None
    assert isinstance(mg.find_node('_pyi_gdal'), modulegraph.SourceModule)


def test_swig_import_from_top_level(tmpdir):
    # While there is a SWIG wrapper module as expected, the package module already imports the "C" module in the
    # same way the SWIG wrapper would do.
    # See the issue #1522 (at about 2017-04-26), pull-request #2578 and commit 711e9e77c93a979a63648ba05f725b30dbb7c3cc.
    #
    # For Python > 2.6, SWIG tries to import the C module from the package's directory and if this fails,
    # uses "import _XXX" (which is the code triggering import in modulegraph). For Python 2, this is a relative import,
    # but for Python 3, this is an absolute import.
    #
    # In this test-case, the package's __init__.py contains code equivalent to the SWIG wrapper-module, causing the C
    # module to be searched as an absolute import (in Python 3). But the importing module is not a SWIG candidate
    # (names do not match), leading to the (absolute) C module to become a MissingModule - which is okay up to this
    # point. Now if the SWIG wrapper-module imports the C module, there already is this MissingModule, inhibiting
    # modulegraph's SWIG import mechanism.
    #
    # This is where the commit 711e9e77c93 steps in and tries to reimport the C module (relative to the
    # SWIG wrapper-module).
    libdir = tmpdir.join('lib')
    path = [str(libdir)]
    osgeo = libdir.join('pyi_test_osgeo')
    osgeo.join('__init__.py').ensure().write('import _pyi_gdal')
    osgeo.join('pyi_gdal.py').write('# automatically generated by SWIG\n' 'import _pyi_gdal')
    osgeo.join('_pyi_gdal.py').write('#')

    script = tmpdir.join('script.py')
    script.write('from pyi_test_osgeo import pyi_gdal')
    mg = modulegraph.ModuleGraph(path)
    mg.add_script(str(script))

    assert isinstance(mg.find_node('pyi_test_osgeo'), modulegraph.Package)
    assert isinstance(mg.find_node('pyi_test_osgeo.pyi_gdal'), modulegraph.SourceModule)
    # The "C" module is frozen under its unqualified rather than qualified name.
    # See comment in modulegraph._safe_import_hook.
    # Due the the buggy implementation (see test_swig_import_simple):
    assert isinstance(mg.find_node('pyi_test_osgeo._pyi_gdal'), modulegraph.SourceModule)
    assert mg.find_node('_pyi_gdal') is None
    # This would be the correct implementation:
    #assert mg.find_node('pyi_test_osgeo._pyi_gdal') is None
    #assert isinstance(mg.find_node('_pyi_gdal'), modulegraph.SourceModule)


def test_swig_import_from_top_level_missing(tmpdir):
    # Like test_swig_import_from_top_level, but the "C" module is missing and should be reported as a MissingModule.
    libdir = tmpdir.join('lib')
    path = [str(libdir)]
    osgeo = libdir.join('pyi_test_osgeo')
    osgeo.join('__init__.py').ensure().write('import _pyi_gdal')
    osgeo.join('pyi_gdal.py').write('# automatically generated by SWIG\n' 'import _pyi_gdal')
    # no module '_pyi_gdal.py'

    script = tmpdir.join('script.py')
    script.write('from pyi_test_osgeo import pyi_gdal')
    mg = modulegraph.ModuleGraph(path)
    mg.add_script(str(script))
    assert isinstance(mg.find_node('pyi_test_osgeo'), modulegraph.Package)
    assert isinstance(mg.find_node('pyi_test_osgeo.pyi_gdal'), modulegraph.SourceModule)
    # BUG: Again, this is unecpected behaviour in modulegraph: While MissingModule('_pyi_gdal') is (arguably) removed
    # when trying to import the SWIG C module, there is no MissingModule('pyi_test_osgeo.pyi_gdal') added, but again
    # MissingModule('_pyi_gdal'). I still need to understand why.
    assert mg.find_node('pyi_test_osgeo._pyi_gdal') is None
    assert isinstance(mg.find_node('_pyi_gdal'), modulegraph.MissingModule)


def test_swig_import_from_top_level_but_nested(tmpdir):
    # Like test_swig_import_from_top_level, but both the wrapper and the "top level" are nested.
    # This is intented to test relative import of the "C" module.
    libdir = tmpdir.join('lib')
    path = [str(libdir)]
    osgeo = libdir.join('pyi_test_osgeo')
    osgeo.join('__init__.py').ensure().write('#')
    osgeo.join('x', '__init__.py').ensure().write('#')
    osgeo.join('x', 'y', '__init__.py').ensure().write('import _pyi_gdal')
    osgeo.join('x', 'y', 'pyi_gdal.py').write('# automatically generated by SWIG\n' 'import _pyi_gdal')
    osgeo.join('x', 'y', '_pyi_gdal.py').write('#')

    script = tmpdir.join('script.py')
    script.write('from pyi_test_osgeo.x.y import pyi_gdal')
    mg = modulegraph.ModuleGraph(path)
    mg.add_script(str(script))

    assert isinstance(mg.find_node('pyi_test_osgeo.x.y.pyi_gdal'), modulegraph.SourceModule)
    # The "C" module is frozen under its unqualified rather than qualified name.
    # See comment in modulegraph._safe_import_hook.
    # Due the the buggy implementation (see test_swig_import_simple):
    assert isinstance(mg.find_node('pyi_test_osgeo.x.y._pyi_gdal'), modulegraph.SourceModule)
    assert mg.find_node('_pyi_gdal') is None
    # This would be the correct implementation:
    #assert mg.find_node('pyi_test_osgeo.x.y._pyi_gdal') is None
    #assert isinstance(mg.find_node('_pyi_gdal'), modulegraph.SourceModule)


def test_swig_top_level_but_no_swig_at_all(tmpdir):
    # From the script import an absolute module which looks like a SWIG candidate but is no SWIG module.
    # See issue #3040 ('_decimal').
    # The center of this test-case is that it does not raise a recursion too deep error.
    libdir = tmpdir.join('lib')
    path = [str(libdir)]
    libdir.join('pyi_dezimal.py').ensure().write('import _pyi_dezimal')
    # no module '_pyi_dezimal.py'

    script = tmpdir.join('script.py')
    script.write('import pyi_dezimal')
    mg = modulegraph.ModuleGraph(path)
    mg.add_script(str(script))
    assert isinstance(mg.find_node('pyi_dezimal'), modulegraph.SourceModule)
    assert isinstance(mg.find_node('_pyi_dezimal'), modulegraph.MissingModule)


def test_swig_top_level_but_no_swig_at_all_existing(tmpdir):
    # Like test_swig_top_level_but_no_swig_at_all, but the "C" module exists.
    # The test-case is here for symmetry.
    libdir = tmpdir.join('lib')
    path = [str(libdir)]
    libdir.join('pyi_dezimal.py').ensure().write('import _pyi_dezimal')
    libdir.join('_pyi_dezimal.py').ensure().write('#')

    script = tmpdir.join('script.py')
    script.write('import pyi_dezimal')
    mg = modulegraph.ModuleGraph(path)
    mg.add_script(str(script))
    assert isinstance(mg.find_node('pyi_dezimal'), modulegraph.SourceModule)
    assert isinstance(mg.find_node('_pyi_dezimal'), modulegraph.SourceModule)


def test_swig_candidate_but_not_swig(tmpdir):
    # From a package module import an absolute module which looks like a SWIG candidate, but is no SWIG module.
    # See issue #2911 (tifffile).
    # The center of this test-case is that it does not raise a recursion too deep error.
    libdir = tmpdir.join('lib')
    path = [str(libdir)]
    pkg = libdir.join('pkg')
    pkg.join('__init__.py').ensure().write('from . import mymod')
    pkg.join('mymod.py').write('import _mymod')
    pkg.join('_mymod.py').write('#')

    script = tmpdir.join('script.py')
    script.write('from pkg import XXX')
    mg = modulegraph.ModuleGraph(path)
    mg.add_script(str(script))
    assert isinstance(mg.find_node('pkg'), modulegraph.Package)
    assert isinstance(mg.find_node('pkg.mymod'), modulegraph.SourceModule)
    assert mg.find_node('pkg._mymod') is None
    # This is not a SWIG module, thus the SWIG import mechanism should not trigger.
    assert isinstance(mg.find_node('_mymod'), modulegraph.MissingModule)


def test_swig_candidate_but_not_swig2(tmpdir):
    """
    Variation of test_swig_candidate_but_not_swig using differnt import statements
    (like tifffile/tifffile.py does).
    """
    libdir = tmpdir.join('lib')
    path = [str(libdir)]
    pkg = libdir.join('pkg')
    pkg.join('__init__.py').ensure().write('from . import mymod')
    pkg.join('mymod.py').write('from . import _mymod\n' 'import _mymod')
    pkg.join('_mymod.py').write('#')

    script = tmpdir.join('script.py')
    script.write('from pkg import XXX')
    mg = modulegraph.ModuleGraph(path)
    mg.add_script(str(script))
    assert isinstance(mg.find_node('pkg'), modulegraph.Package)
    assert isinstance(mg.find_node('pkg.mymod'), modulegraph.SourceModule)
    assert isinstance(mg.find_node('pkg._mymod'), modulegraph.SourceModule)
    assert isinstance(mg.find_node('_mymod'), modulegraph.MissingModule)


def test_swig_candidate_but_not_swig_missing(tmpdir):
    # Like test_swig_candidate_but_not_swig, but the "C" module is missing and should be reported as a MissingModule.
    libdir = tmpdir.join('lib')
    path = [str(libdir)]
    pkg = libdir.join('pkg')
    pkg.join('__init__.py').ensure().write('from . import mymod')
    pkg.join('mymod.py').write('import _mymod')
    # no module '_mymod.py'

    script = tmpdir.join('script.py')
    script.write('import pkg')
    mg = modulegraph.ModuleGraph(path)
    mg.add_script(str(script))
    assert isinstance(mg.find_node('pkg'), modulegraph.Package)
    assert isinstance(mg.find_node('pkg.mymod'), modulegraph.SourceModule)
    assert mg.find_node('pkg._mymod') is None
    assert isinstance(mg.find_node('_mymod'), modulegraph.MissingModule)


def test_swig_candidate_but_not_swig_missing2(tmpdir):
    """
    Variation of test_swig_candidate_but_not_swig_missing using differnt import statements
    (like tifffile/tifffile.py does).
    """
    libdir = tmpdir.join('lib')
    path = [str(libdir)]
    pkg = libdir.join('pkg')
    pkg.join('__init__.py').ensure().write('from . import mymod')
    pkg.join('mymod.py').write('from . import _mymod\n' 'import _mymod')
    # no module '_mymod.py'

    script = tmpdir.join('script.py')
    script.write('import pkg')
    mg = modulegraph.ModuleGraph(path)
    mg.add_script(str(script))
    assert isinstance(mg.find_node('pkg'), modulegraph.Package)
    assert isinstance(mg.find_node('pkg.mymod'), modulegraph.SourceModule)
    assert isinstance(mg.find_node('pkg._mymod'), modulegraph.MissingModule)
    assert isinstance(mg.find_node('_mymod'), modulegraph.MissingModule)
