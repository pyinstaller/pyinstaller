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

import ast
import importlib.machinery
import os
import sys
import py_compile
import textwrap
import zipfile

import pytest

from PyInstaller.lib.modulegraph import modulegraph
from PyInstaller.utils.tests import xfail


def _import_and_get_node(tmp_path, module_name, path=None):
    script = tmp_path / 'script.py'
    script.write_text(f"import {module_name}", encoding='utf-8')
    if path is None:
        path = [str(tmp_path)]
    mg = modulegraph.ModuleGraph(path)
    mg.add_script(str(script))
    return mg.find_node(module_name)


def test_sourcefile(tmp_path):
    (tmp_path / 'source.py').write_text("###", encoding='utf-8')
    node = _import_and_get_node(tmp_path, 'source')
    assert isinstance(node, modulegraph.SourceModule)


def test_invalid_sourcefile(tmp_path):
    (tmp_path / 'invalid_source.py').write_text("invalid python-source code", encoding='utf-8')
    node = _import_and_get_node(tmp_path, 'invalid_source')
    assert isinstance(node, modulegraph.InvalidSourceModule)


def test_invalid_compiledfile(tmp_path):
    (tmp_path / 'invalid_compiled.pyc').write_text("invalid byte-code", encoding='utf-8')
    node = _import_and_get_node(tmp_path, 'invalid_compiled')
    assert isinstance(node, modulegraph.InvalidCompiledModule)


def test_builtin(tmp_path):
    node = _import_and_get_node(tmp_path, 'sys', path=sys.path)
    assert isinstance(node, modulegraph.BuiltinModule)


def test_extension(tmp_path):
    node = _import_and_get_node(tmp_path, '_ctypes', path=sys.path)
    assert isinstance(node, modulegraph.Extension)


def test_package(tmp_path):
    # Create package; stuff/__init__.py
    (tmp_path / 'stuff').mkdir()
    pysrc = tmp_path / 'stuff' / '__init__.py'
    pysrc.write_text("###", encoding='utf-8')
    # Analyze
    node = _import_and_get_node(tmp_path, 'stuff')
    assert node.__class__ is modulegraph.Package
    assert node.filename in (str(pysrc), str(pysrc) + 'c')
    assert node.packagepath == [str(pysrc.parent)]


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
def test_package_init_is_extension(tmp_path, num, modname, expected_nodetype):
    # Regression: Recursion too deep

    EXTENSION_SUFFIX = importlib.machinery.EXTENSION_SUFFIXES[0]

    def _write_module(*args):
        module_file = tmp_path.joinpath(*args)
        module_file.parent.mkdir(parents=True, exist_ok=True)
        module_file.write_text('###', encoding='utf-8')
        return module_file

    def create_package_files(test_case):
        m = _write_module('myextpkg', '__init__' + EXTENSION_SUFFIX)
        if test_case == 1:
            return m
        _write_module('myextpkg', '__init__.py')
        if test_case == 2:
            return m  # return extension module anyway
        m = _write_module('myextpkg', 'other.py')
        m = _write_module('myextpkg', 'other' + EXTENSION_SUFFIX)
        if test_case == 3:
            return m
        m = _write_module('myextpkg', 'subpkg', '__init__.py')
        m = _write_module('myextpkg', 'subpkg', '__init__' + EXTENSION_SUFFIX)
        if test_case == 4:
            return m
        m = _write_module('myextpkg', 'subpkg', 'other.py')
        m = _write_module('myextpkg', 'subpkg', 'other' + EXTENSION_SUFFIX)
        return m

    module_file = create_package_files(num)
    node = _import_and_get_node(tmp_path, modname)
    assert node.__class__ is expected_nodetype
    if expected_nodetype is modulegraph.ExtensionPackage:
        assert node.packagepath == [str(module_file.parent)]
    else:
        assert node.packagepath is None  # not a package
    assert node.filename == str(module_file)


#-- Basic tests - these seem to be missing in the original modulegraph test-suite


def test_relative_import_missing(tmp_path):
    libdir = tmp_path / 'lib'

    pkg = libdir / 'pkg'
    (pkg / 'x' / 'y').mkdir(parents=True)  # Create the whole package directory tree
    (pkg / '__init__.py').write_text("#", encoding='utf-8')
    (pkg / 'x' / '__init__.py').write_text("#", encoding='utf-8')
    (pkg / 'x' / 'y' / '__init__.py').write_text("#", encoding='utf-8')
    (pkg / 'x' / 'y' / 'z.py').write_text("from . import DoesNotExist", encoding='utf-8')

    script = tmp_path / 'script.py'
    script.write_text("import pkg.x.y.z", encoding='utf-8')

    mg = modulegraph.ModuleGraph([str(libdir)])
    mg.add_script(str(script))
    assert isinstance(mg.find_node('pkg.x.y.z'), modulegraph.SourceModule)
    assert isinstance(mg.find_node('pkg.x.y.DoesNotExist'), modulegraph.MissingModule)


#-- Tests with a single module in a zip-file


def test_zipped_module_source(tmp_path):
    pysrc = tmp_path / 'stuff.py'
    pysrc.write_text("###", encoding='utf-8')

    zipfilename = tmp_path / 'unstuff.zip'
    with zipfile.ZipFile(zipfilename, mode='w') as zfh:
        zfh.write(pysrc, 'stuff.py')

    node = _import_and_get_node(tmp_path, 'stuff', path=[zipfilename])
    assert node.__class__ is modulegraph.SourceModule
    assert node.filename.startswith(os.path.join(zipfilename, 'stuff.py'))


def test_zipped_module_source_and_compiled(tmp_path):
    pysrc = tmp_path / 'stuff.py'
    pysrc.write_text("###", encoding='utf-8')

    pyc = pysrc.with_suffix('.pyc')
    py_compile.compile(pysrc, pyc)

    zipfilename = tmp_path / 'unstuff.zip'
    with zipfile.ZipFile(zipfilename, mode='w') as zfh:
        zfh.write(pysrc, 'stuff.py')
        zfh.write(pyc, 'stuff.pyc')

    node = _import_and_get_node(tmp_path, 'stuff', path=[zipfilename])
    # Do not care whether it is source or compiled, as long as it is neither invalid nor missing.
    assert node.__class__ in (modulegraph.SourceModule, modulegraph.CompiledModule)
    assert node.filename.startswith(os.path.join(zipfilename, 'stuff.py'))


#-- Tests with a package in a zip-file


def test_zipped_package_source(tmp_path):
    pkg = tmp_path / 'stuff'
    pkg.mkdir()

    pysrc = pkg / '__init__.py'
    pysrc.write_text('###', encoding='utf-8')

    zipfilename = tmp_path / 'stuff.zip'
    with zipfile.ZipFile(zipfilename, mode='w') as zfh:
        zfh.write(pkg, 'stuff')
        zfh.write(pysrc, 'stuff/__init__.py')

    node = _import_and_get_node(tmp_path, 'stuff', path=[zipfilename])
    assert node.__class__ is modulegraph.Package
    assert node.packagepath == [os.path.join(zipfilename, 'stuff')]


def test_zipped_package_source_and_compiled(tmp_path):
    pkg = tmp_path / 'stuff'
    pkg.mkdir()

    pysrc = pkg / '__init__.py'
    pysrc.write_text('###', encoding='utf-8')

    pyc = pysrc.with_suffix('.pyc')
    py_compile.compile(pysrc, pyc)

    zipfilename = tmp_path / 'stuff.zip'
    with zipfile.ZipFile(zipfilename, mode='w') as zfh:
        zfh.write(pkg, 'stuff')
        zfh.write(pysrc, 'stuff/__init__.py')
        zfh.write(pyc, 'stuff/__init__.pyc')

    node = _import_and_get_node(tmp_path, 'stuff', path=[zipfilename])
    assert node.__class__ is modulegraph.Package
    assert node.packagepath == [os.path.join(zipfilename, 'stuff')]


#-- Namespace packages


def test_nspackage_pep420(tmp_path):
    p1 = tmp_path / 'p1'
    (p1 / 'stuff').mkdir(parents=True)
    (p1 / 'stuff' / 'a.py').write_text("###", encoding='utf-8')

    p2 = tmp_path / 'p2'
    (p2 / 'stuff').mkdir(parents=True)
    (p2 / 'stuff' / 'b.py').write_text("###", encoding='utf-8')

    path = [str(p1), str(p2)]

    script = tmp_path / 'script.py'
    script.write_text("import stuff.a, stuff.b", encoding='utf-8')

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
def test_symlinks(tmp_path):
    (tmp_path / 'p1').mkdir()
    p1_init = tmp_path / 'p1' / '__init__.py'
    p1_init.write_text("###", encoding='utf-8')

    (tmp_path / 'p2').mkdir()
    p2_init = tmp_path / 'p2' / '__init__.py'
    p2_init.write_text("###", encoding='utf-8')

    base_dir = tmp_path / 'base'
    (base_dir / 'p1').mkdir(parents=True)

    os.symlink(str(p1_init), str(base_dir / 'p1' / '__init__.py'))
    os.symlink(str(p2_init), str(base_dir / 'p1' / 'p2.py'))

    node = _import_and_get_node(base_dir, 'p1.p2')
    assert isinstance(node, modulegraph.SourceModule)


def test_import_order_1(tmp_path):
    # Ensure modulegraph processes modules in the same order as Python does.

    class MyModuleGraph(modulegraph.ModuleGraph):
        def _load_module(self, fqname, pathname, loader):
            if not record or record[-1] != fqname:
                record.append(fqname)  # record non-consecutive entries
            return super()._load_module(fqname, pathname, loader)

    record = []

    # (filename, content)
    ENTRIES = (
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
    )

    for filename, content in ENTRIES:
        if filename.endswith('/'):
            filename += '__init__'
        filename += '.py'
        module_fullpath = tmp_path / filename
        module_fullpath.parent.mkdir(parents=True, exist_ok=True)
        module_fullpath.write_text(content, encoding='utf-8')

    script = tmp_path / 'script.py'
    script.write_text("import a, b", encoding='utf-8')

    mg = MyModuleGraph([str(tmp_path)])
    mg.add_script(str(script))

    # This is the order Python imports these modules given that script.
    expected = [
        'a', 'a.c', 'a.d', 'a.d.f', 'a.d.f.j', 'a.d.f.k', 'a.d.g', 'a.d.g.l', 'a.d.g.m', 'a.d.h', 'b', 'b.e', 'b.e.i'
    ]
    assert record == expected


def test_import_order_2(tmp_path):
    # Ensure modulegraph processes modules in the same order as Python does.

    class MyModuleGraph(modulegraph.ModuleGraph):
        def _load_module(self, fqname, pathname, loader):
            if not record or record[-1] != fqname:
                record.append(fqname)  # record non-consecutive entries
            return super()._load_module(fqname, pathname, loader)

    record = []

    # (filename, content)
    ENTRIES = (
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
    )

    for filename, content in ENTRIES:
        if filename.endswith('/'):
            filename += '__init__'
        filename += '.py'
        module_fullpath = tmp_path / filename
        module_fullpath.parent.mkdir(parents=True, exist_ok=True)
        module_fullpath.write_text(content, encoding='utf-8')

    script = tmp_path / 'script.py'
    script.write_text("import b.f.n.p", encoding='utf-8')

    mg = MyModuleGraph([str(tmp_path)])
    mg.add_script(str(script))

    # This is the order Python imports these modules given that script.
    expected = [
        'b', 'b.e', 'a', 'a.c', 'a.c.g', 'b.e.k', 'b.f', 'b.f.n', 'b.f.n.p', 'b.e.l', 'a.d', 'a.d.j', 'a.d.i', 'a.c.h'
    ]
    assert record == expected


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


def _test_swig_import_simple_common(tmp_path):
    libdir = tmp_path / 'lib'

    osgeo = libdir / 'pyi_test_osgeo'
    osgeo.mkdir(parents=True)
    (osgeo / '__init__.py').write_text('#', encoding='utf-8')
    (osgeo / '_pyi_gdal.py').write_text("#", encoding='utf-8')
    (osgeo / 'pyi_gdal.py').write_text(
        "\n".join(["# automatically generated by SWIG", "import _pyi_gdal"]),
        encoding='utf-8',
    )

    script = tmp_path / 'script.py'
    script.write_text("from pyi_test_osgeo import pyi_gdal", encoding='utf-8')

    mg = modulegraph.ModuleGraph([str(libdir)])
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
    return mg  # for use in test_swig_import_simple


def test_swig_import_simple_BUGGY(tmp_path):
    # Test the currently implemented behavior of SWIG support.
    _test_swig_import_simple_common(tmp_path)


@xfail
def test_swig_import_simple(tmp_path):
    # Test the expected (but not implemented) behavior of SWIG support.
    mg = _test_swig_import_simple_common(tmp_path)
    # Given the bug in modulegraph (see test_swig_import_simple_BUGGY) this is what would be the expected behavior.
    # TODO: When modulegraph is fixed, merge the two test-cases and correct test_swig_import_from_top_level
    # and siblings.
    assert mg.find_node('pyi_test_osgeo._pyi_gdal') is None
    assert isinstance(mg.find_node('_pyi_gdal'), modulegraph.SourceModule)


def test_swig_import_from_top_level(tmp_path):
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
    libdir = tmp_path / 'lib'

    osgeo = libdir / 'pyi_test_osgeo'
    osgeo.mkdir(parents=True)
    (osgeo / '__init__.py').write_text("import _pyi_gdal", encoding='utf-8')
    (osgeo / '_pyi_gdal.py').write_text("#", encoding='utf-8')
    (osgeo / 'pyi_gdal.py').write_text(
        "\n".join(["# automatically generated by SWIG", "import _pyi_gdal"]),
        encoding='utf-8',
    )

    script = tmp_path / 'script.py'
    script.write_text("from pyi_test_osgeo import pyi_gdal", encoding='utf-8')

    mg = modulegraph.ModuleGraph([str(libdir)])
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


def test_swig_import_from_top_level_missing(tmp_path):
    # Like test_swig_import_from_top_level, but the "C" module is missing and should be reported as a MissingModule.
    libdir = tmp_path / 'lib'

    osgeo = libdir / 'pyi_test_osgeo'
    osgeo.mkdir(parents=True)
    (osgeo / '__init__.py').write_text("import _pyi_gdal", encoding='utf-8')
    (osgeo / 'pyi_gdal.py').write_text(
        "\n".join(["# automatically generated by SWIG", "import _pyi_gdal"]),
        encoding='utf-8',
    )

    script = tmp_path / 'script.py'
    script.write_text("from pyi_test_osgeo import pyi_gdal", encoding='utf-8')

    mg = modulegraph.ModuleGraph([str(libdir)])
    mg.add_script(str(script))

    assert isinstance(mg.find_node('pyi_test_osgeo'), modulegraph.Package)
    assert isinstance(mg.find_node('pyi_test_osgeo.pyi_gdal'), modulegraph.SourceModule)
    assert isinstance(mg.find_node('pyi_test_osgeo._pyi_gdal'), modulegraph.MissingModule)
    assert mg.find_node('_pyi_gdal') is None


def test_swig_import_from_top_level_but_nested(tmp_path):
    # Like test_swig_import_from_top_level, but both the wrapper and the "top level" are nested.
    # This is intended to test relative import of the "C" module.
    libdir = tmp_path / 'lib'

    osgeo = libdir / 'pyi_test_osgeo'
    (osgeo / 'x' / 'y').mkdir(parents=True)  # Create whole package directory tree.
    (osgeo / '__init__.py').write_text("#", encoding='utf-8')
    (osgeo / 'x' / '__init__.py').write_text("#", encoding='utf-8')
    (osgeo / 'x' / 'y' / '__init__.py').write_text("import _pyi_gdal", encoding='utf-8')
    (osgeo / 'x' / 'y' / '_pyi_gdal.py').write_text('#', encoding='utf-8')
    (osgeo / 'x' / 'y' / 'pyi_gdal.py').write_text(
        "\n".join(["# automatically generated by SWIG", "import _pyi_gdal"]),
        encoding='utf-8',
    )

    script = tmp_path / 'script.py'
    script.write_text("from pyi_test_osgeo.x.y import pyi_gdal", encoding='utf-8')

    mg = modulegraph.ModuleGraph([str(libdir)])
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


def test_swig_top_level_but_no_swig_at_all(tmp_path):
    # From the script import an absolute module which looks like a SWIG candidate but is no SWIG module.
    # See issue #3040 ('_decimal').
    # The center of this test-case is that it does not raise a recursion too deep error.
    libdir = tmp_path / 'lib'
    libdir.mkdir()
    (libdir / 'pyi_dezimal.py').write_text("import _pyi_dezimal", encoding='utf-8')

    script = tmp_path / 'script.py'
    script.write_text("import pyi_dezimal", encoding='utf-8')

    mg = modulegraph.ModuleGraph([str(libdir)])
    mg.add_script(str(script))

    assert isinstance(mg.find_node('pyi_dezimal'), modulegraph.SourceModule)
    assert isinstance(mg.find_node('_pyi_dezimal'), modulegraph.MissingModule)


def test_swig_top_level_but_no_swig_at_all_existing(tmp_path):
    # Like test_swig_top_level_but_no_swig_at_all, but the "C" module exists.
    # The test-case is here for symmetry.
    libdir = tmp_path / 'lib'
    libdir.mkdir()
    (libdir / 'pyi_dezimal.py').write_text("import _pyi_dezimal", encoding='utf-8')
    (libdir / '_pyi_dezimal.py').write_text("#", encoding='utf-8')

    script = tmp_path / 'script.py'
    script.write_text("import pyi_dezimal", encoding='utf-8')

    mg = modulegraph.ModuleGraph([str(libdir)])
    mg.add_script(str(script))

    assert isinstance(mg.find_node('pyi_dezimal'), modulegraph.SourceModule)
    assert isinstance(mg.find_node('_pyi_dezimal'), modulegraph.SourceModule)


def test_swig_candidate_but_not_swig(tmp_path):
    # From a package module import an absolute module which looks like a SWIG candidate, but is no SWIG module.
    # See issue #2911 (tifffile).
    # The center of this test-case is that it does not raise a recursion too deep error.
    libdir = tmp_path / 'lib'

    pkg = libdir / 'pkg'
    pkg.mkdir(parents=True)
    (pkg / '__init__.py').write_text("from . import mymod", encoding='utf-8')
    (pkg / 'mymod.py').write_text("import _mymod", encoding='utf-8')
    (pkg / '_mymod.py').write_text("#", encoding='utf-8')

    script = tmp_path / 'script.py'
    script.write_text("from pkg import XXX", encoding='utf-8')

    mg = modulegraph.ModuleGraph([str(libdir)])
    mg.add_script(str(script))

    assert isinstance(mg.find_node('pkg'), modulegraph.Package)
    assert isinstance(mg.find_node('pkg.mymod'), modulegraph.SourceModule)
    assert mg.find_node('pkg._mymod') is None
    # This is not a SWIG module, thus the SWIG import mechanism should not trigger.
    assert isinstance(mg.find_node('_mymod'), modulegraph.MissingModule)


def test_swig_candidate_but_not_swig2(tmp_path):
    """
    Variation of test_swig_candidate_but_not_swig using different import statements
    (like tifffile/tifffile.py does).
    """
    libdir = tmp_path / 'lib'

    pkg = libdir / 'pkg'
    pkg.mkdir(parents=True)
    (pkg / '__init__.py').write_text("from . import mymod", encoding='utf-8')
    (pkg / '_mymod.py').write_text("#", encoding='utf-8')
    (pkg / 'mymod.py').write_text(
        "\n".join(["from . import _mymod", "import _mymod"]),
        encoding='utf-8',
    )

    script = tmp_path / 'script.py'
    script.write_text("from pkg import XXX", encoding='utf-8')

    mg = modulegraph.ModuleGraph([str(libdir)])
    mg.add_script(str(script))

    assert isinstance(mg.find_node('pkg'), modulegraph.Package)
    assert isinstance(mg.find_node('pkg.mymod'), modulegraph.SourceModule)
    assert isinstance(mg.find_node('pkg._mymod'), modulegraph.SourceModule)
    assert isinstance(mg.find_node('_mymod'), modulegraph.MissingModule)


def test_swig_candidate_but_not_swig_missing(tmp_path):
    # Like test_swig_candidate_but_not_swig, but the "C" module is missing and should be reported as a MissingModule.
    libdir = tmp_path / 'lib'

    pkg = libdir / 'pkg'
    pkg.mkdir(parents=True)
    (pkg / '__init__.py').write_text("from . import mymod", encoding='utf-8')
    (pkg / 'mymod.py').write_text("import _mymod", encoding='utf-8')

    script = tmp_path / 'script.py'
    script.write_text("import pkg", encoding='utf-8')

    mg = modulegraph.ModuleGraph([str(libdir)])
    mg.add_script(str(script))

    assert isinstance(mg.find_node('pkg'), modulegraph.Package)
    assert isinstance(mg.find_node('pkg.mymod'), modulegraph.SourceModule)
    assert mg.find_node('pkg._mymod') is None
    assert isinstance(mg.find_node('_mymod'), modulegraph.MissingModule)


def test_swig_candidate_but_not_swig_missing2(tmp_path):
    """
    Variation of test_swig_candidate_but_not_swig_missing using different import statements
    (like tifffile/tifffile.py does).
    """
    libdir = tmp_path / 'lib'

    pkg = libdir / 'pkg'
    pkg.mkdir(parents=True)
    (pkg / '__init__.py').write_text("from . import mymod", encoding='utf-8')
    (pkg / 'mymod.py').write_text(
        "\n".join(["from . import _mymod", "import _mymod"]),
        encoding='utf-8',
    )

    script = tmp_path / 'script.py'
    script.write_text("import pkg", encoding='utf-8')

    mg = modulegraph.ModuleGraph([str(libdir)])
    mg.add_script(str(script))

    assert isinstance(mg.find_node('pkg'), modulegraph.Package)
    assert isinstance(mg.find_node('pkg.mymod'), modulegraph.SourceModule)
    assert isinstance(mg.find_node('pkg._mymod'), modulegraph.MissingModule)
    assert isinstance(mg.find_node('_mymod'), modulegraph.MissingModule)
