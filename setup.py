"""
PyInstaller is a program that converts (packages) Python programs into
stand-alone executables, under Windows, Linux, and Mac OS X. Its main
advantages over similar tools are that PyInstaller works with any
version of Python since 2.2, it builds smaller executables thanks to
transparent compression, it is fully multi-platform, and use the OS
support to load the dynamic libraries, thus ensuring full
compatibility.

The main goal of PyInstaller is to be compatible with 3rd-party
packages out-of-the-box. This means that, with PyInstaller, all the
required tricks to make external packages work are already integrated
within PyInstaller itself so that there is no user intervention
required. You'll never be required to look for tricks in wikis and
apply custom modification to your files or your setup scripts. As an
example, libraries like PyQt, Django or matplotlib are fully
supported, without having to handle plugins or external data files
manually.
"""

raise SystemExit("\nsetup.py is not yet supposed to work. "
                 "Please Use PyInstaller without installation.\n")

from setuptools import setup, find_packages

import platform
import itertools
import glob
import os

scripts = [
    'pyinstaller.py',
    'pyinstaller-gui.py',
    'utils/ArchiveViewer.py',
    #'utils/BinDepend.py',
    'utils/Build.py',
    'utils/Configure.py',
    #'utils/Crypt.py',
    #'utils/GrabVersion.py',
    'utils/Makespec.py',
]

if platform.system() == "Windows":
    scripts.append('MakeComServer.py')

def find_data_files(*patterns):
    data_files = {}
    for fn in itertools.chain(*(glob.iglob(p) for p in patterns)):
        if os.path.isfile(fn):
            data_files.setdefault(os.path.dirname(fn), []).append(fn)
    return data_files.items()

setup(
    name = 'pyinstaller',
    version = '1.6.0dev',
    scripts = scripts,
    packages = find_packages(),
    data_files = find_data_files('doc/*',
                                 'doc/images/*', 'doc/stylesheets/*.css',
                                 'support/*.py', 'support/rthooks/*.py',
                                 'support/loader/*', 'support/loader/*/*'),
    author = "Gordon McMillan, William Caban, Giovanni Bajo and the PyInstaller team",
    author_email = "pyinstaller@googlegroups.com",
    maintainer = "Giovanni Bajo and the PyInstaller team",
    maintainer_email = "pyinstaller@googlegroups.com",
    description = "Converts (packages) Python programs into stand-alone executables, under Windows, Linux, and Mac OS X.",
    long_description = __doc__,
    license = ("GPL license with a special exception which allows to use "
               "PyInstaller to build and distribute non-free programs "
               "(including commercial ones)."),
    keywords = "packaging, standalone executable, freeze",
    url = "http://www.pyinstaller.org/",
    download_url = "http://www.pyinstaller.org/wiki#Downloads",    
    zip_safe = False,
    classifiers = [
        'Development Status :: 6 - Mature',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.3',
        'Programming Language :: Python :: 2.4',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: C',
        'Topic :: Software Development :: Build Tools',
        'Topic :: System :: Software Distribution',
        ]
    )
