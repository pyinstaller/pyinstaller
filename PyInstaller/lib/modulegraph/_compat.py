import sys

if sys.version_info[0] == 2:
    def Bchr(value):
        return chr(value)

else:
    def Bchr(value):
        return value
