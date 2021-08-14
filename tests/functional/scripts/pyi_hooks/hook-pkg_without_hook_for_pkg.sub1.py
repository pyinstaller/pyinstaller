import PyInstaller.hooks
import os
from importlib.util import find_spec

NAME = 'pkg_without_hook_for_pkg.sub1'

# 1. ensure self-test is working by searching for _this_ hook
hookmodnm = 'hook-' + NAME
searchpath = PyInstaller.hooks.__path__ + [os.path.dirname(__file__)]
assert find_spec(hookmodnm, searchpath) is not None, "Error in the hook's self-test"

# 2. The actual self-test: there must be no hook for the parent module
hookmodnm = 'hook-pkg_without_hook_for_pkg'
try:
    assert find_spec(hookmodnm, searchpath), 'Self-test of hook %s failed: hook for parent exists' % NAME
except ImportError as e:
    if e.name != hookmodnm:
        raise Exception('Self-test of hook %s failed: hook for parent exists and has import errors.' % NAME)

# The actual hook part
hiddenimports = ['pkg_without_hook_for_pkg.sub1.sub11']
