"""
Enough Mach-O to make your head spin.

See the relevant header files in /usr/include/mach-o

And also Apple's documentation.
"""
import pkg_resources
__version__ = pkg_resources.require('macholib')[0].version

