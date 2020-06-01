[metadata]
name = pyinstaller
version = attr: PyInstaller.__version__
url = http://www.pyinstaller.org/

description = PyInstaller bundles a Python application and all its dependencies into a single package.
# Long description consists of README.rst and doc/CHANGES.rst.
# PYPI page will contain complete PyInstaller changelog.
long_description = file: README.rst, doc/_dummy-roles.txt, doc/CHANGES.rst

author = Hartmut Goebel, Giovanni Bajo, David Vierra, David Cortesi, Martin Zibricky


keywords =
    packaging, app, apps, bundle, convert, standalone, executable
	pyinstaller, cxfreeze, freeze, py2exe, py2app, bbfreeze

license = GPLv2-or-later with a special exception which allows to use PyInstaller to build and distribute non-free programs (including commercial ones)
license_file = COPYING.txt

classifiers =
    Development Status :: 6 - Mature
    Environment :: Console
    Intended Audience :: Developers
    Intended Audience :: Other Audience
    Intended Audience :: System Administrators
    License :: OSI Approved :: GNU General Public License v2 (GPLv2)
    Natural Language :: English
    Operating System :: MacOS :: MacOS X
    Operating System :: Microsoft :: Windows
    Operating System :: POSIX
    Operating System :: POSIX :: AIX
    Operating System :: POSIX :: BSD
    Operating System :: POSIX :: Linux
    Operating System :: POSIX :: SunOS/Solaris
    Programming Language :: C
    Programming Language :: Python
    Programming Language :: Python :: 3
    Programming Language :: Python :: 3 :: Only
    Programming Language :: Python :: 3.5
    Programming Language :: Python :: 3.6
    Programming Language :: Python :: 3.7
    Programming Language :: Python :: Implementation :: CPython
    Topic :: Software Development
    Topic :: Software Development :: Build Tools
    Topic :: Software Development :: Interpreters
    Topic :: Software Development :: Libraries :: Python Modules
    Topic :: System :: Installation/Setup
    Topic :: System :: Software Distribution
    Topic :: Utilities

[options]
zip_safe = False
packages = PyInstaller
include_package_data = True
## IMPORTANT: Keep aligned with requirements.txt
install_requires =
    setuptools
    altgraph
    pefile >= 2017.8.1 ; sys_platform == 'win32'
    pywin32-ctypes >= 0.2.0 ; sys_platform == 'win32'
    macholib >= 1.8 ; sys_platform == 'darwin'

[options.extras_require]
; for 3rd-party packages testing their hooks in their CI:
hook_testing =
    pytest >= 2.7.3
    execnet >= 1.5.0
    psutil
encryption =
    tinyaes>=1.0.0

[options.package_data]
# This includes precompiled bootloaders and icons for bootloaders
PyInstaller: bootloader/*/*
# This file is necessary for rthooks (runtime hooks)
PyInstaller.hooks: rthooks.dat
# Needed for tests discovered by entry points;
# see ``PyInstaller/utils/run_tests.py``.
PyInstaller.utils: pytest.ini

[options.entry_points]
console_scripts =
	pyinstaller = PyInstaller.__main__:run
    pyi-archive_viewer = PyInstaller.utils.cliutils.archive_viewer:run
    pyi-bindepend = PyInstaller.utils.cliutils.bindepend:run
    pyi-grab_version = PyInstaller.utils.cliutils.grab_version:run
    pyi-makespec = PyInstaller.utils.cliutils.makespec:run
    pyi-set_version = PyInstaller.utils.cliutils.set_version:run

[sdist]
# For release distribution generate .tar.gz archives only. These are
# about 10% smaller then .zip files.
formats=gztar

#[bdist_wheel]
# We MUST NOT create an universal wheel as PyInstaller has different
# dependencies per platforms and version and includes compiled binaries.
#universal = MUST NOT


[zest.releaser]
python-file-with-version = PyInstaller/__init__.py
# This entry point ensures signing of tgz/zip archive before uploading to PYPI.
# This is required untill release supports passing `--sign` to twine.
releaser.before_upload = PyInstaller.utils.release.sign_source_distribution

push-changes = no
tag-format = v{version}
tag-message = PyInstaller {version}
tag-signing = yes


[catchlog]
# Restrict log-level to DEBUG because py.test cannot handle the volume of
# messages that TRACE produces.
log_level = DEBUG

[tool:pytest]
# Do not put timeout to all tests because it does not play nice with running
# tests in parallel. Rather put timeout to single tests: that are known to
#      @pytest.mark.timeout(timeout=0)
# 'thread' timeout method adds more overhead but works in Travis containers.
timeout_method = thread

# Look for tests only in tests directories.
# Later we could change this to just "tests/**/test_*.py"
python_files = "tests/functional/test_*.py" "tests/unit/test_*.py"

# Don't search test-data for test-cases
norecursedirs:
   tests/functional/data
   tests/functional/logs
   tests/functional/modules
   tests/functional/scripts
   tests/functional/specs
   tests/scripts
   tests/unit/Tree_files
   tests/unit/hookutils_files
   tests/unit/test_modulegraph/testdata
   tests/unit/test_modulegraph/testpkg-*


# Display summary info for (s)skipped, (X)xpassed, (x)xfailed, (f)failed and (e)errored tests
# Skip doctest text files
# If you want to run just a subset of test use command
#
#   pytest -k test_name
#
addopts = "-v" "-rsxXfE" "--doctest-glob="

[flake8]
exclude =
   .git,
   doc/_build,
   build,
   dist,
   bootloader
show-source = True
# E265 - block comment should start with '# '
ignore = E265
