#-----------------------------------------------------------------------------
# Copyright (c) 2015-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
# Botocore is a low-level interface to a growing number of Amazon Web Services.
# Botocore serves as the foundation for the AWS-CLI command line utilities. It
# will also play an important role in the boto3.x project.
#
# The botocore package is compatible with Python versions 2.6.5, Python 2.7.x,
# and Python 3.3.x and higher.
#
# https://botocore.readthedocs.org/en/latest/
#
# Tested with botocore 1.4.36

from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.compat import is_py2
from PyInstaller.utils.hooks import is_module_satisfies

if is_module_satisfies('botocore >= 1.4.36'):
    if is_py2:
        hiddenimports = ['HTMLParser']
    else:
        hiddenimports = ['html.parser']

datas = collect_data_files('botocore')
