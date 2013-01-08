# same test of test-ctypes-cdll-c.py, but built in one-file mode
import ctypes, ctypes.util

# Make sure we are able to load the MSVCRXX.DLL we are currently bound
# to through ctypes.
lib = ctypes.CDLL(ctypes.util.find_library('c'))
print lib
