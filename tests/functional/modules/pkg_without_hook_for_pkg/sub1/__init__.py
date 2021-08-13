#

print('This is module ' + __name__)

# Tick: import a package in a way, PyInstaller is not able to track it. But we want to import it anyway to make the
# submodule `sub11` print it's name.
sub11 = ''.join('sub11')
__import__(__name__ + '.' + sub11, globals=globals(), level=0)
