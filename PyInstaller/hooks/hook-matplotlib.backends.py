#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.compat import is_darwin
from PyInstaller.utils.hooks import (
    eval_statement, exec_statement, logger)


def get_matplotlib_backend_module_names():
    """
    List the names of all matplotlib backend modules importable under the
    current Python installation.

    Returns
    ----------
    list
        List of the fully-qualified names of all such modules.
    """
    # Statement safely importing a single backend module.
    import_statement = """
import os, sys

# Preserve stdout.
sys_stdout = sys.stdout

try:
    # Redirect output printed by this importation to "/dev/null", preventing
    # such output from being erroneously interpreted as an error.
    with open(os.devnull, 'w') as dev_null:
        sys.stdout = dev_null
        __import__('%s')
# If this is an ImportError, print this exception's message without a traceback.
# ImportError messages are human-readable and require no additional context.
except ImportError as exc:
    sys.stdout = sys_stdout
    print(exc)
# Else, print this exception preceded by a traceback. traceback.print_exc()
# prints to stderr rather than stdout and must not be called here!
except Exception:
    sys.stdout = sys_stdout
    import traceback
    print(traceback.format_exc())
"""

    # List of the human-readable names of all available backends.
    backend_names = eval_statement(
        'import matplotlib; print(matplotlib.rcsetup.all_backends)')

    # List of the fully-qualified names of all importable backend modules.
    module_names = []

    # If the current system is not OS X and the "CocoaAgg" backend is available,
    # remove this backend from consideration. Attempting to import this backend
    # on non-OS X systems halts the current subprocess without printing output
    # or raising exceptions, preventing its reliable detection.
    if not is_darwin and 'CocoaAgg' in backend_names:
        backend_names.remove('CocoaAgg')

    # For safety, attempt to import each backend in a unique subprocess.
    for backend_name in backend_names:
        module_name = 'matplotlib.backends.backend_%s' % backend_name.lower()
        stdout = exec_statement(import_statement % module_name)

        # If no output was printed, this backend is importable.
        if not stdout:
            module_names.append(module_name)
            logger.info('  Matplotlib backend "%s": added' % backend_name)
        else:
            logger.info('  Matplotlib backend "%s": ignored\n    %s' % (backend_name, stdout))

    return module_names

# Freeze all importable backends, as PyInstaller is unable to determine exactly
# which backends are required by the current program.
hiddenimports = get_matplotlib_backend_module_names()
