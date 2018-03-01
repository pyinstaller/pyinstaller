#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
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
import argparse
import platform
import sys


from . import __version__
from . import log as logging

# note: don't import anything else until this function is run!
from .compat import check_requirements

logger = logging.getLogger(__name__)


def run_makespec(filenames, **opts):
    # Split pathex by using the path separator
    temppaths = opts['pathex'][:]
    pathex = opts['pathex'] = []
    for p in temppaths:
        pathex.extend(p.split(os.pathsep))

    import PyInstaller.building.makespec

    spec_file = PyInstaller.building.makespec.main(filenames, **opts)
    logger.info('wrote %s' % spec_file)
    return spec_file


def run_build(pyi_config, spec_file, **kwargs):
    import PyInstaller.building.build_main
    PyInstaller.building.build_main.main(pyi_config, spec_file, **kwargs)


def __add_options(parser):
    parser.add_argument('-v', '--version', action='version',
                        version=__version__,
                        help='Show program version info and exit.')

def run(pyi_args=None, pyi_config=None):
    """
    pyi_args     allows running PyInstaller programatically without a subprocess
    pyi_config   allows checking configuration once when running multiple tests
    """
    check_requirements()
    
    import PyInstaller.building.makespec
    import PyInstaller.building.build_main
    import PyInstaller.log

    try:
        parser = argparse.ArgumentParser()
        __add_options(parser)
        PyInstaller.building.makespec.__add_options(parser)
        PyInstaller.building.build_main.__add_options(parser)
        PyInstaller.log.__add_options(parser)
        parser.add_argument('filenames', metavar='scriptname', nargs='+',
                            help=("name of scriptfiles to be processed or "
                                  "exactly one .spec-file. If a .spec-file is "
                                  "specified, most options are unnecessary "
                                  "and are ignored."))

        args = parser.parse_args(pyi_args)
        PyInstaller.log.__process_options(parser, args)

        # Print PyInstaller version, Python version and platform
        # as the first line to stdout.
        # This helps identify PyInstaller, Python and platform version
        #  when users report issues.
        logger.info('PyInstaller: %s' % __version__)
        logger.info('Python: %s' % platform.python_version())
        logger.info('Platform: %s' % platform.platform())

        # Skip creating .spec when .spec file is supplied
        if args.filenames[0].endswith('.spec'):
            spec_file = args.filenames[0]
        else:
            spec_file = run_makespec(**vars(args))

        run_build(pyi_config, spec_file, **vars(args))

    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")


if __name__ == '__main__':
    run()
