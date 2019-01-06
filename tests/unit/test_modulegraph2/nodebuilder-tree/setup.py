import os
import sys
from setuptools import setup, Extension, Command
import py_compile
import zipfile

extension1 = Extension("extension", sources=["extension1.c"])
extension2 = Extension("package.pkgext", sources=["pkgext.c"])
extension3 = Extension("ext_package.__init__", sources=["init.c"])


class build_bytecode(Command):
    description = "build bytecode modules"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        for dirname, dirs, files in os.walk("src"):
            for fn in files:
                if fn.endswith(".py"):
                    srcpath = os.path.join(dirname, fn)
                    dstpath = srcpath[4:] + "c"
                    py_compile.compile(srcpath, dstpath, dstpath[:-1], True)

        with zipfile.ZipFile("packages.zip", "w") as zf:
            for dirname, dirs, files in os.walk("zipsrc"):
                for fn in files:
                    srcpath = os.path.join(dirname, fn)
                    dstpath = srcpath[7:]
                    zf.write(srcpath, dstpath)

setup(
    ext_modules=[extension1, extension2, extension3],
    cmdclass={"build_bytecode": build_bytecode},
)
