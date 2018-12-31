import sys
from setuptools import setup, Extension

extension = Extension("extension", sources=["extension.c"])

if sys.platform != "win32":
    # Dynamicly create this file because it has a
    # name that is invalid on Windows
    with open('package/my"data.txt', "w") as fp:
        fp.write("This is on odd data file")

setup(
    name="simple-package",
    version="1.0",
    description="This is a demo package",
    include_package_data=True,
    packages=["package"],
    py_modules=["toplevel"],
    ext_modules=[extension],
)
