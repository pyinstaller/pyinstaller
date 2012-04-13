from ctypes import *
import ctypes.util
import usb.backend.libusb10 as libusb10
import usb.backend.libusb01 as libusb01
import usb.backend.openusb as openusb
import os, sys
import glob

def get_load_func(type, candidates):
  def _load_library():
    if sys._MEIPASS is not None:
      exec_path = sys._MEIPASS
    else:
      exec_path = os.dir.realpath(os.path.dirname(sys.argv[0]))

    l = None
    for candidate in candidates:
      # doing linker's path lookup work to force load bundled copy
      if os.name == "posix" and sys.platform == "darwin":
        libs = glob.glob("%s/%s*.dylib*" % (exec_path, candidate))
      elif sys.platform == 'win32':
        libs = glob.glob("%s\\%s*.dll" % (exec_path, candidate))
      else:
        libs = glob.glob("%s/%s*.so*" % (exec_path, candidate))
      for libname in libs:
        try:
          # libusb01 is using CDLL under win32 (see usb.backends.libusb01)
          if sys.platform == 'win32' and type != 'libusb01':
            l = WinDLL(libname)
          else:
            l = CDLL(libname)
          if l is not None: break
        except:
          l = None
      if l is not None: break
    else:
      raise OSError('USB library could not be found')

    if type == 'libusb10':
      # Windows backend uses stdcall calling convention
      # On FreeBSD 8/9, libusb 1.0 and libusb 0.1 are in the same shared
      # object libusb.so, so if we found libusb library name, we must assure
      # it is 1.0 version. We just try to get some symbol from 1.0 version
      if not hasattr(l, 'libusb_init'):
        raise OSError('USB library could not be found')
    return l
  return _load_library

# NOTE: need to keep in sync with future PyUSB updates
libusb10._load_library = get_load_func('libusb10', ('usb-1.0', 'libusb-1.0', 'usb'))
libusb01._load_library = get_load_func('libusb01', ('usb-0.1', 'usb', 'libusb0'))
openusb._load_library  = get_load_func('openusb', ('openusb', ))
