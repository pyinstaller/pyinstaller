#!/bin/bash
#
# Two arguments:
# $1 is the filename of a python file for example test_email
# $2 is the path leading to it within the "test" directory
# $3 if given is additional PyInstaller options
# for example:
#     $1=test_5 and $2=basic, test is tests/basic/test_5.py
#     $1=relimp1 and $2=import/relimp, test is tests/import/relimp/relimp1.py
# the point being, $1 is the name of the folder and executable, too
if [ -z $1 ]
then
    echo "usage: $0 testname subdir-in-tests [options] "
    exit -1
fi
if [ -z $2 ]
then
    echo "usage: $0 testname subdir-in-tests [options] "
    exit -1
fi
EXTRA_OPTIONS=$3
if [ -z $EXTRA_OPTIONS ] ; then
    EXTRA_OPTIONS='.'
fi
SCRATCH=~/Desktop/scratch
DEV=/Users/original/Dropbox/David/PPQT/pyidev
DEV2=$DEV/v2
DEV3=$DEV/v3

# Kludge - TODO - why does unmodified v2 archive_viewer not work?
ARCHIVE_VIEWER="/Users/original/Dropbox/David/PPQT/pyidev/v3/PyInstaller/cliutils/archive_viewer.py"
export ARCHIVE_VIEWER

echo "testing $2/$1.py with original code"
time ./buildx.bash $1 $2 "$EXTRA_OPTIONS" $DEV2 $SCRATCH/v2
echo
echo "testing $2/$1.py with development code"
time ./buildx.bash $1 $2 "$EXTRA_OPTIONS" $DEV3 $SCRATCH/v3
echo
bbedit $SCRATCH/v2/$1.log.txt
bbedit $SCRATCH/v3/$1.log.txt
