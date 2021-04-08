import sys
from setuptools import setup, Extension

extension = Extension("package._example", sources=["library_wrap.c", "library.c"])

setup(ext_modules=[extension])
