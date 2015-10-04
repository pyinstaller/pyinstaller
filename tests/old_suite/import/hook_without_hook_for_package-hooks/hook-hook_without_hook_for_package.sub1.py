hiddenimports = ['hook_without_hook_for_package.sub1.sub11']

NAME = 'hook_without_hook_for_package.sub1'

# self-test for this test-case:
import PyInstaller.hooks
import os
# TODO For Python 3 replace this by importlib, imp is deprecated
import imp

# 1. ensure self-test is working by searching for _this_ hook
hookmodnm = 'hook-' + NAME
searchpath = PyInstaller.hooks.__path__ + [os.path.dirname(__file__)]
assert imp.find_module(hookmodnm, searchpath) is not None

# 2. The actual self-test: there must be no hook for the parent module
hookmodnm = 'hook-hook_without_hook_for_package'
try:
    imp.find_module(hookmodnm, searchpath)
    raise Exception('Self-test of hook %s failed: hook for parent exists'
                    % NAME)
except ImportError as e:
    if (hasattr(e, 'name') and e.name == hookmodnm): # python3
        pass # okay
    elif  not e.args[0].endswith(' '+hookmodnm): # python2
        raise Exception('Self-test of hook %s failed: hook for parent exists '
                        'and has import errors.' % NAME)
