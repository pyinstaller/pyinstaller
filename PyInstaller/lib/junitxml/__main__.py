"""Command line functionality for junitxml.

:Author: Duncan Findlay <duncan@duncf.ca>
"""
import sys

import junitxml.main

if __name__ == '__main__':
    if sys.argv[0].endswith('__main__.py'):
        sys.argv[0] = 'python -m junitxml'
    junitxml.main.main()
