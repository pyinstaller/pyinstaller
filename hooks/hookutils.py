#!/usr/bin/env python

def exec_statement(stat):
    """Executes a Python statement in an externally spawned interpreter, and
    returns anything that was emitted in the standard output as a single string.
    """

    import os, tempfile, sys

    fnm = tempfile.mktemp()
    exe = sys.executable

    # Using "echo on" as a workaround for a bug in NT4 shell
    if os.name == "nt":
        cmd = '"echo on && "%s" -c "%s" > "%s""' % (exe, stat, fnm)
    else:
        cmd = '"%s" -c "%s" > "%s"' % (exe, stat, fnm)
    os.system(cmd)

    txt = open(fnm, 'r').read()[:-1]
    os.remove(fnm)
    return txt

def qt4_plugins_dir():
    return exec_statement("from PyQt4.QtCore import QLibraryInfo; print QLibraryInfo.location(QLibraryInfo.PluginsPath)")
def mpl_data_dir():
    return exec_statement("import matplotlib; print matplotlib._get_data_path()")
def qwt_numpy_support():
    return eval(exec_statement("from PyQt4 import Qwt5; print hasattr(Qwt5, 'toNumpy')"))
def qwt_numeric_support():
    return eval(exec_statement("from PyQt4 import Qwt5; print hasattr(Qwt5, 'toNumeric')"))
def qwt_numarray_support():
    return eval(exec_statement("from PyQt4 import Qwt5; print hasattr(Qwt5, 'toNumarray')"))
