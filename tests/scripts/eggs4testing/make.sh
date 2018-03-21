#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# This file is part of the package for testing eggs in `PyInstaller`.

NSPKG_1="nspkg1-aaa nspkg1-bbb nspkg1-ccc nspkg1-empty"
NSPKG_2="nspkg2-aaa nspkg2-bbb nspkg2-ccc nspkg2-empty"
NSPKG_3="nspkg3-aaa nspkg3-bbb nspkg3-ccc nspkg3-empty"

distdir="$PWD"/dist
testsdir="$PWD"/../import

export PYTHONDONTWRITEBYTECODE=1

rm -rf build/ dist/ *.egg* */*.egg* */build/ */dist/ venv
rm -rf $NSPKG_1 $NSPKG_2 $NSPKG_3

./build-nspkg-tests.py

# We need to clean up build-dir between builds, otherwise stuff from
# one egg goes into the next one.
python setup-zipped.py bdist_egg --dist-dir "$distdir"
rm -rf build/
python setup-unzipped.py bdist_egg --dist-dir "$distdir"
rm -rf build/

for pkg in $NSPKG_1 $NSPKG_3 ; do
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
easy_install "$distdir"/nspkg{1,3}_*.egg
for pkg in $NSPKG_2 ; do
    cd $pkg
    python setup.py install --single-version-externally-managed \
	--record=install.log
    cd -
done
cp $testsdir/test_{eggs,nspkg{1,2,3}}*.py venv

# see if the unpackaged test-case still works
cd venv
python test_eggs1.py
python test_eggs2.py
python test_nspkg1.py
python test_nspkg1-bbb-zzz.py
python test_nspkg1-empty.py
python test_nspkg2.py
python test_nspkg3.py
# Need to move nspkg3_aaa*.egg out of the path. Otherwise
# pkgutil.extend_path() would add the namespace `nspkg3` from the egg
# and cut of the zipped eggs. This is an implementation restriction of
# pkgutil.extend_path().
mkdir .off
mv lib/python*/site-packages/nspkg3_aaa*.egg .off
python test_nspkg3-bbb-zzz.py
python test_nspkg3-empty.py
mv .off/* lib/python*/site-packages/
cd ..

cd venv
rm -rf $testsdir/{,un}zipped.egg $testsdir/nspkg{1,2,3}*-pkg
mv lib/python*/site-packages/zipped_egg-*.egg $testsdir/zipped.egg
mv lib/python*/site-packages/unzipped_egg-*.egg $testsdir/unzipped.egg

pkgdir=$testsdir/nspkg1-pkg
mkdir -p $pkgdir
for pkg in $NSPKG_1 ; do
    pkg=${pkg/-/_}
    mv lib/python*/site-packages/$pkg-*.egg $pkgdir/$pkg.egg
done

pkgdir=$testsdir/nspkg3-pkg
mkdir -p $pkgdir
for pkg in $NSPKG_3 ; do
    pkg=${pkg/-/_}
    mv lib/python*/site-packages/$pkg-*.egg $pkgdir/$pkg.egg
done

pkgdir=$testsdir/nspkg2-pkg
mkdir -p $pkgdir
mv lib/python*/site-packages/nspkg2/ $pkgdir
for pkg in $NSPKG_2 ; do
    pkg=${pkg/-/_}
    mv lib/python*/site-packages/$pkg-*.egg-info/ $pkgdir/$pkg.egg-info
    mv lib/python*/site-packages/$pkg-*-nspkg.pth $pkgdir/$pkg-nspkg.pth
done

cd ..

deactivate

#rm -rf build/ dist/ *.egg* */*.egg* */build/ */dist/ venv
