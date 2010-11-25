#!/usr/bin/env python

import os

def exec_statement(stat):
    """Executes a Python statement in an externally spawned interpreter, and
    returns anything that was emitted in the standard output as a single string.
    """

    import os, tempfile, sys

    fnm = tempfile.mktemp()
    exe = sys.executable

    # Using "echo on" as a workaround for a bug in NT4 shell
    if os.name == "nt":
        cmd = 'echo on && "%s" -c "%s" > "%s"' % (exe, stat, fnm)
    else:
        cmd = '"%s" -c "%s" > "%s"' % (exe, stat, fnm)

    # Prepend PYTHONPATH with pathex
    pp = os.pathsep.join(sys.pathex)
    old_pp = os.environ.get('PYTHONPATH', '')
    if old_pp:
        pp = os.pathsep.join([pp, old_pp])
    os.environ["PYTHONPATH"] = pp
    try:
        # Actually execute the statement
        os.system(cmd)
    finally:
        if old_pp:
            os.environ["PYTHONPATH"] = old_pp
        else:
            del os.environ["PYTHONPATH"]

    txt = open(fnm, 'r').read()[:-1]
    os.remove(fnm)
    return txt

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
def babel_localedata_dir():
    return exec_statement("import babel.localedata; print babel.localedata._dirname")
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
    os.environ["DJANGO_SETTINGS_MODULE"] = "%s.settings" %package_name
    return eval(exec_statement("execfile(r'%s')" %os.path.join(os.path.dirname(__file__), "django-import-finder.py")))

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
