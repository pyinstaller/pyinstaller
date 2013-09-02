#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# This file is part of the package for testing eggs in `PyInstaller`.

NSPKG_1="nspkg1-aaa nspkg1-bbb nspkg1-ccc nspkg1-empty"
NSPKG_2="nspkg2-aaa nspkg2-bbb nspkg2-ccc nspkg2-empty"

distdir="$PWD"/dist

export PYTHONDONTWRITEBYTECODE=1

rm -rf build/ dist/ *.egg* */*.egg* */build/ */dist/ venv
rm -rf $NSPKG_1 $NSPKG_2

./build-nspkg-tests.py


python setup-zipped.py bdist_egg
# nedd to clean up build-dir, otherwise stuff from `zipped_egg`
# goes into `unzipped_egg*.egg`
rm -rf build/
python setup-unzipped.py bdist_egg
rm -rf build/

for pkg in $NSPKG_1 ; do
    cd $pkg
    python setup.py sdist --dist-dir "$distdir"
    python setup.py bdist_egg --dist-dir "$distdir"
    cd -
done

# setup a virtualenv for testing
virtualenv venv --distribute
. venv/bin/activate
easy_install --zip-ok "$distdir"/zipped_egg*.egg
easy_install --always-unzip "$distdir"/unzipped_egg*.egg
easy_install "$distdir"/nspkg1_*.egg
for pkg in $NSPKG_2 ; do
    cd $pkg
    python setup.py install --single-version-externally-managed \
	--record=install.log
    cd -
done
cp ../import/test_{eggs,nspkg{1,2}}*.py venv

# see if the unpackaged test-case still works
cd venv
python test_eggs1.py
python test_eggs2.py
python test_nspkg1.py
python test_nspkg1-bbb-zzz.py
python test_nspkg1-empty.py
python test_nspkg2.py
cd ..

cd venv
rm -rfv ../../import/{,un}zipped.egg ../../import/nspkg{1,2}*-pkg
mv -v lib/python2.7/site-packages/zipped_egg-*.egg ../../import/zipped.egg
mv -v lib/python2.7/site-packages/unzipped_egg-*.egg ../../import/unzipped.egg

pkgdir=../../import/nspkg1-pkg
mkdir -p $pkgdir
for pkg in $NSPKG_1 ; do
    pkg=${pkg/-/_}
    mv -v lib/python2.7/site-packages/$pkg-*.egg $pkgdir/$pkg.egg
done

pkgdir=../../import/nspkg2-pkg
mkdir -p $pkgdir
mv -v lib/python2.7/site-packages/nspkg2/ $pkgdir
for pkg in $NSPKG_2 ; do
    pkg=${pkg/-/_}
    mv -v lib/python2.7/site-packages/$pkg-*.egg-info/ $pkgdir/$pkg.egg-info
    mv -v lib/python2.7/site-packages/$pkg-*-nspkg.pth $pkgdir/$pkg-nspkg.pth
done

cd ..

deactivate

#rm -rf build/ dist/ *.egg* */*.egg* */build/ */dist/ venv
