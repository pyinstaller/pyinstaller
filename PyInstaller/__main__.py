#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Main command-line interface to PyInstaller.
"""

import os
import optparse
import platform
import sys

import PyInstaller.building.makespec
import PyInstaller.building.build_main
import PyInstaller.compat
import PyInstaller.log


from . import __version__
from .compat import check_requirements
from .utils import misc
from . import log as logging

logger = logging.getLogger(__name__)


def run_makespec(opts, args):
    # Split pathex by using the path separator
    temppaths = opts.pathex[:]
    opts.pathex = []
    for p in temppaths:
        opts.pathex.extend(p.split(os.pathsep))

    spec_file = PyInstaller.building.makespec.main(args, **opts.__dict__)
    logger.info('wrote %s' % spec_file)
    return spec_file


def run_build(opts, spec_file, pyi_config):
    PyInstaller.building.build_main.main(pyi_config, spec_file, **opts.__dict__)


def __add_options(parser):
    parser.add_option('-v', '--version', default=False, action='store_true',
                      help='Show program version info and exit.')

def run(pyi_args=sys.argv[1:], pyi_config=None):
    """
    pyi_args     allows running PyInstaller programatically without a subprocess
    pyi_config   allows checking configuration once when running multiple tests
    """
    misc.check_not_running_as_root()
    check_requirements()


    try:
        parser = optparse.OptionParser(
            usage='%prog [opts] <scriptname> [ <scriptname> ...] | <specfile>'
            )
        __add_options(parser)
        PyInstaller.building.makespec.__add_options(parser)
        PyInstaller.building.build_main.__add_options(parser)
        PyInstaller.log.__add_options(parser)
        PyInstaller.compat.__add_obsolete_options(parser)

        opts, args = parser.parse_args(pyi_args)
        PyInstaller.log.__process_options(parser, opts)

        # Print program version and exit
        if opts.version:
            print(__version__)
            raise SystemExit(0)

        if not args:
            parser.error('Requires at least one scriptname file '
                         'or exactly one .spec-file')

        # Print PyInstaller version, Python version and platform
        # as the first line to stdout.
        # This helps identify PyInstaller, Python and platform version
        #  when users report issues.
        logger.info('PyInstaller: %s' % __version__)
        logger.info('Python: %s' % platform.python_version())
        logger.info('Platform: %s' % platform.platform())

        # Skip creating .spec when .spec file is supplied
        if args[0].endswith('.spec'):
            spec_file = args[0]
        else:
            spec_file = run_makespec(opts, args)

        run_build(opts, spec_file, pyi_config)

    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")


if __name__ == '__main__':
    run()
