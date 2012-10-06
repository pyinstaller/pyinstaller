import ctypes.util
import os

def find_library_decorator(func):
    def wrapper(name):
        lib = func(name)
        if lib == None:
            lib_path = os.path.join(sys._MEIPASS, name)
            lib - func(lib_path)
        return lib
    return wrapper

ctypes.util.find_library = find_library_decorator(ctypes.util.find_library)
