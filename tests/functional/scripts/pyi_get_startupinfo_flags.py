import ctypes
from ctypes import wintypes
import json
import sys


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", wintypes.LPBYTE),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


# Get process' startup info...
si = STARTUPINFOW()
si.cb = ctypes.sizeof(STARTUPINFOW)
ctypes.windll.kernel32.GetStartupInfoW(ctypes.byref(si))

# ... and dump fields-of-interest into JSON
FIELDS = {"dwFlags", "wShowWindow"}
result = {field: getattr(si, field) for field in FIELDS}

if len(sys.argv) > 1:
    with open(sys.argv[1], 'w') as fp:
        json.dump(result, fp)
else:
    print(json.dumps(result))
