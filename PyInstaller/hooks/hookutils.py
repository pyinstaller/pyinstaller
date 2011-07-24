#!/usr/bin/env python

import os, sys, subprocess


def exec_statement(statement):
    """Executes a Python statement in an externally spawned interpreter, and
    returns anything that was emitted in the standard output as a single string.
    """

    cmd = [sys.executable, '-c', statement]

    # Prepend PYTHONPATH with pathex
    pp = os.pathsep.join(sys.path)
    old_pp = os.environ.get('PYTHONPATH', '')
    if old_pp:
        pp = os.pathsep.join([pp, old_pp])
    os.environ["PYTHONPATH"] = pp
    try:
        try:
            txt = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
        except OSError, e:
            raise SystemExit("Execution failed: %s" % e)
    finally:
        if old_pp:
            os.environ["PYTHONPATH"] = old_pp
        else:
            del os.environ["PYTHONPATH"]
    return txt[:-1]



def dlls_in_dir(directory):
    """Returns *.dll, *.so, *.dylib in given directories)"""
    from glob import glob
    d = directory
    files = []
    files.extend(glob('%s/*.so' % d))
    files.extend(glob('%s/*.dll' % d))
    files.extend(glob('%s/*.dylib' % d))
    return files


def qt4_plugins_dir():
    import os
    qt4_plugin_dirs = eval(exec_statement("from PyQt4.QtCore import QCoreApplication; app=QCoreApplication([]); print map(unicode,app.libraryPaths())"))
    if not qt4_plugin_dirs:
        print "E: Cannot find PyQt4 plugin directories"
        return ""
    for d in qt4_plugin_dirs:
        if os.path.isdir(d):
            return str(d)  # must be 8-bit chars for one-file builds
    print "E: Cannot find existing PyQt4 plugin directory"
    return ""


def qt4_phonon_plugins_dir():
    import os
    qt4_plugin_dirs = eval(exec_statement("from PyQt4.QtGui import QApplication; app=QApplication([]); app.setApplicationName('pyinstaller'); from PyQt4.phonon import Phonon; v=Phonon.VideoPlayer(Phonon.VideoCategory); print map(unicode,app.libraryPaths())"))
    if not qt4_plugin_dirs:
        print "E: Cannot find PyQt4 phonon plugin directories"
        return ""
    for d in qt4_plugin_dirs:
        if os.path.isdir(d):
            return str(d)  # must be 8-bit chars for one-file builds
    print "E: Cannot find existing PyQt4 phonon plugin directory"
    return ""


def qt4_plugins_binaries(plugin_type):
    """Return list of dynamic libraries formated for mod.binaries."""
    from os.path import basename, join
    binaries = []
    pdir = qt4_plugins_dir()
    files = dlls_in_dir(join(pdir, plugin_type))
    for f in files:
        binaries.append((
            join('qt4_plugins', plugin_type, basename(f)),
            f, 'BINARY'))
    return binaries


def babel_localedata_dir():
    return exec_statement("import babel.localedata; print babel.localedata._dirname")


def enchant_win32_data_files():
    files = eval(exec_statement("import enchant; print enchant.utils.win32_data_files()"))
    datas = []  # data files in PyInstaller hook format
    for d in files:
        for f in d[1]:
            datas.append((f, d[0]))
    return datas


def mpl_data_dir():
    return exec_statement("import matplotlib; print matplotlib._get_data_path()")


def qwt_numpy_support():
    return eval(exec_statement("from PyQt4 import Qwt5; print hasattr(Qwt5, 'toNumpy')"))


def qwt_numeric_support():
    return eval(exec_statement("from PyQt4 import Qwt5; print hasattr(Qwt5, 'toNumeric')"))


def qwt_numarray_support():
    return eval(exec_statement("from PyQt4 import Qwt5; print hasattr(Qwt5, 'toNumarray')"))


def django_dottedstring_imports(django_root_dir):
    package_name = os.path.basename(django_root_dir)
    os.environ["DJANGO_SETTINGS_MODULE"] = "%s.settings" % package_name
    return eval(exec_statement("execfile(r'%s')" % os.path.join(os.path.dirname(__file__), "django-import-finder.py")))


def find_django_root(dir):
    entities = os.listdir(dir)
    if "manage.py" in entities and "settings.py" in entities and "urls.py" in entities:
        return [dir]
    else:
        django_root_directories = []
        for entity in entities:
            path_to_analyze = os.path.join(dir, entity)
            if os.path.isdir(path_to_analyze):
                dir_entities = os.listdir(path_to_analyze)
                if "manage.py" in dir_entities and "settings.py" in dir_entities and "urls.py" in dir_entities:
                    django_root_directories.append(path_to_analyze)
        return django_root_directories
