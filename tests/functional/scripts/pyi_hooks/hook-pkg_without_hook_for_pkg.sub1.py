
hiddenimports = ['pkg_without_hook_for_pkg.sub1.sub11']

NAME = 'pkg_without_hook_for_pkg.sub1'

# self-test for this test-case:
import PyInstaller.hooks
import os

from PyInstaller.compat import is_py2
if is_py2:
    import imp

    def find_module(hookmodnm, searchpath):
        return imp.find_module(hookmodnm, searchpath)
else:
    import importlib.util

    def find_module(hookmodnm, searchpath):
        return importlib.util.find_module(hookmodnm, searchpath)

# 1. ensure self-test is working by searching for _this_ hook
hookmodnm = 'hook-' + NAME
searchpath = PyInstaller.hooks.__path__ + [os.path.dirname(__file__)]
assert find_module(hookmodnm, searchpath) is not None, "Error in the hook's self-test"

# 2. The actual self-test: there must be no hook for the parent module
hookmodnm = 'hook-pkg_without_hook_for_pkg'
try:
    find_module(hookmodnm, searchpath)
    raise Exception('Self-test of hook %s failed: hook for parent exists'
                    % NAME)
except ImportError as e:
    if (hasattr(e, 'name') and e.name == hookmodnm): # python3
        pass # okay
    elif  not e.args[0].endswith(' '+hookmodnm): # python2
        raise Exception('Self-test of hook %s failed: hook for parent exists '
                        'and has import errors.' % NAME)
