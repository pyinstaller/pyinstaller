hiddenimports = ['hook_without_hook_for_package.sub1.sub11']

NAME = 'hook_without_hook_for_package.sub1'

# self-test for this test-case:
import PyInstaller.hooks
import imp
# 1. ensure self-test is working by searching for _this_ hook
hookmodnm = 'hook-' + NAME
assert imp.find_module(hookmodnm, PyInstaller.hooks.__path__) is not None
# 2. The actual self-test: there must be no hook for the parent module
hookmodnm = 'hook-hook_without_hook_for_package'
try:
    imp.find_module(hookmodnm, PyInstaller.hooks.__path__)
    raise Exception('Self-test of hook %s failed: hook for parent exists'
                    % NAME)
except ImportError, e:
    if not e.args[0].endswith(' '+hookmodnm):
        raise Exception('Self-test of hook %s failed: hook for parent exists '
                        'and has import errors.' % NAME)
