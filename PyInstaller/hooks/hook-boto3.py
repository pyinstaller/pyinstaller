#-----------------------------------------------------------------------------
# Copyright (c) 2015-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
# Boto is the Amazon Web Services (AWS) SDK for Python, which allows Python
# developers to write software that makes use of Amazon services like S3 and
# EC2. Boto provides an easy to use, object-oriented API as well as low-level
# direct service access.
#
# http://boto3.readthedocs.org/en/latest/
#
# Tested with boto3 1.2.1

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = (
    collect_submodules('boto3.dynamodb') +
    collect_submodules('boto3.ec2') +
    collect_submodules('boto3.s3')
)
datas = collect_data_files('boto3')
