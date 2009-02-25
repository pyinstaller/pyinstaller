#!/usr/bin/env python
from distutils.core import setup
from distutils.extension import Extension

setup(
  name = 'AES',
  ext_modules=[
    Extension("AES", ["AES.c"]),
    ],
)
