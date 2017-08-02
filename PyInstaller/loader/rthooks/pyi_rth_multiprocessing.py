from sys import platform as _platform

# 'spawn' multiprocessing needs some adjustments on osx
if _platform == 'darwin':
    import sys
    import os
    import re
    import multiprocessing
    import multiprocessing.spawn as spawn

    # prevent spawn from trying to read __main__ in from the main script
    multiprocessing.process.ORIGINAL_DIR = None

    def _freeze_support():
        if 'multiprocessing.semaphore_tracker' in sys.argv[-1]:
            m = re.compile('.*main\((\d+)\)$').match(sys.argv[-1])
            fd = int(m.group(1))
            import multiprocessing.semaphore_tracker
            multiprocessing.semaphore_tracker.main(fd)
            sys.exit()

        if spawn.is_forking(sys.argv):
            kwds = {}
            for arg in sys.argv[2:]:
                name, value = arg.split('=')
                if value == 'None':
                    kwds[name] = None
                else:
                    kwds[name] = int(value)
            spawn.spawn_main(**kwds)
            sys.exit()

    multiprocessing.freeze_support = spawn.freeze_support = _freeze_support

    # Module multiprocessing is organized differently in Python 3.4+
    try:
        # Python 3.4+
        if sys.platform.startswith('win'):
            import multiprocessing.popen_spawn_win32 as forking
        else:
            import multiprocessing.popen_fork as forking
    except ImportError:
        import multiprocessing.forking as forking

    # First define a modified version of Popen.
    class _Popen(forking.Popen):
        def __init__(self, *args, **kw):
            if hasattr(sys, 'frozen'):
                # We have to set original _MEIPASS2 value from sys._MEIPASS
                # to get --onefile mode working.
                os.putenv('_MEIPASS2', sys._MEIPASS)  # @UndefinedVariable
            try:
                super(_Popen, self).__init__(*args, **kw)
            finally:
                if hasattr(sys, 'frozen'):
                    # On some platforms (e.g. AIX) 'os.unsetenv()' is not
                    # available. In those cases we cannot delete the variable
                    # but only set it to the empty string. The bootloader
                    # can handle this case.
                    if hasattr(os, 'unsetenv'):
                        os.unsetenv('_MEIPASS2')
                    else:
                        os.putenv('_MEIPASS2', '')

    forking.Popen = _Popen
   