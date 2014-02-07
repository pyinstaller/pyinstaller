# This is a temporay script for packaging basic Python modules into .zip file.
# The .zip file with basic modules is necessary to have on PYTHONPATH for
# initializing libpython3 in order to run the frozen executable.

# TODO This code should be integrated into PyInstaller


import imp
import io
import marshal
import os
import sys
import zipfile

if __name__ == '__main__':

    mg_home = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'PyInstaller/lib')
    sys.path.insert(0, mg_home)    # Find base modules.
    from modulegraph import find_modules
    from modulegraph import modulegraph

    graph = find_modules.find_modules(includes=
        ('traceback', 'warnings', 'encodings.*', 'importlib._bootstrap')
    )

    # Helper functions.
    def _write_long(f, x):
        """
        Write a 32-bit int to a file in little-endian order.
        """
        f.write(bytes([x        & 0xff,
                      (x >> 8)  & 0xff,
                      (x >> 16) & 0xff,
                      (x >> 24) & 0xff]))

    # Constants same for all .pyc files.
    MAGIC = imp.get_magic()

    # Class zipfile.PyZipFile is not suitable for PyInstaller needs.
    with zipfile.ZipFile('base_library.zip', mode='w') as zf:
        zf.debug = 3
        print('Adding python files')
        for mod in graph.flatten():
            if type(mod) is modulegraph.Package:
                print(30*'A'+' '+mod.identifier)
                print(mod.filename)

            if type(mod) in (modulegraph.SourceModule, modulegraph.Package):
                print(mod.filename)
                # TODO
                st = os.stat(mod.filename)
                timestamp = int(st.st_mtime)
                size = st.st_size & 0xFFFFFFFF
                # Name inside a zip archive.
                # TODO use .pyo suffix if optimize flag is enabled.
                if type(mod) is modulegraph.Package:
                    new_name = mod.identifier.replace('.', os.sep) + os.sep + '__init__' + '.pyc'
                else:
                    new_name = mod.identifier.replace('.', os.sep) + '.pyc'
                print(new_name)

                # Write code to a file.
                # This code is similar to py_compile.compile().
                with io.BytesIO() as fc:
                    # Prepare all data in byte stream file-like object.
                    fc.write(MAGIC)
                    _write_long(fc, timestamp)
                    _write_long(fc, size)
                    marshal.dump(mod.code, fc)
                    zf.writestr(new_name, fc.getvalue())

        # Print files in the zip archive.
        for name in zf.namelist():
            print(name)


