import os, sys
supportdir = os.path.join(sys.path[0], 'support')
genpydir = os.path.join(supportdir, 'gen_py')
initmod = os.path.join(genpydir, '__init__.py')
if not os.path.exists(genpydir):
    os.makedirs(genpydir)
if not os.path.exists(initmod):
    open(initmod, 'w')
import win32com
win32com.__gen_path__ = genpydir
win32com.__path__.insert(0, supportdir)
# for older Pythons
import copy_reg

