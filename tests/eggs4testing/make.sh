#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# This file is part of the package for testing eggs in `PyInstaller`.


export PYTHONDONTWRITEBYTECODE=1

rm -rf build/ dist/ *.egg-info

python setup-zipped.py bdist_egg
# nedd to clean up build-dir, otherwise stuff from `zipped_egg`
# goes into `unzipped_egg*.egg`
rm -rf build/
python setup-unzipped.py bdist_egg
rm -rf build/

# setup a virtualenv for testing
virtualenv venv --distribute
. venv/bin/activate
easy_install --zip-ok dist/zipped_egg*.egg
easy_install --always-unzip dist/unzipped_egg*.egg
cp ../import/test_eggs*.py venv

# see if the unpackaged test-case still works
cd venv
python test_eggs1.py
python test_eggs2.py
cd ..

cd venv
rm -rfv ../../import/zipped.egg ../../import/unzipped.egg
mv -v lib/python2.7/site-packages/zipped_egg-*.egg ../../import/zipped.egg
mv -v lib/python2.7/site-packages/unzipped_egg-*.egg ../../import/unzipped.egg
cd ..

deactivate

rm -rf build/ dist/ venv *.egg-info
