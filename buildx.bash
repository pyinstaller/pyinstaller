#!/bin/bash
#
# Arguments:
# $1 is the filename of a test file for example test_email
# $2 is the path leading to it within the "test" directory
# $3 is additional PyInstaller options or "."
# $4 is the home directory of this version of PyInstaller
# $5 is the target directory to hold build and dist output
#
# Also depends on ARCHIVE_VIEWER TODO fix to use $CLI/archive_viewer.py
#
# This is an internal script and no error checking is done
#
EXTRA_OPTIONS=' '
if [ $3 != '.' ] ; then
    EXTRA_OPTIONS=$3
fi

# punctuation for log file

DIVIDER=" ============ "

# Shorthand names for locations
#
#  - where we put all work and output files, some local dir
#
WORK=$5
BUILD=$WORK/build
DIST=$WORK/dist
#
#  - where the code lives, probably in dropbox
#
DEV=$4
PYI=$DEV/PyInstaller
LDR=$DEV/loader
CLI=$DEV/PyInstaller/cliutils
#
# Save the default PYTHONPATH, we set our own per test
#
ORIGINAL_PYTHONPATH=$PYTHONPATH
#
# create the scratch dir if it doesn't exist.
#
if [ ! -e $WORK ] ; then
    mkdir $WORK
fi
#
# name the output log file and get rid of any previous one
# n.b. the --clean option gets rid of any existing PyI work files
#
LOG=$WORK/$1.log.txt
if [ -e $LOG ] ; then
    rm $LOG
fi
#
# create the log file and initialize with a timestamp and options
#
echo $DIVIDER $1 `date` $DIVIDER > $LOG
#
# set the build options and document them in the log
#
OPTIONS="--distpath=$DIST --specpath=$BUILD --workpath=$BUILD --clean -y $EXTRA_OPTIONS"
echo "options: " $OPTIONS >> $LOG
#
# Run the build
#
cd $DEV
PYTHONPATH=$DEV:$PYI:$LDR
export PYTHONPATH
echo $DIVIDER 'PyInstaller Console' $DIVIDER >> $LOG
COMMAND="python $DEV/pyinstaller.py $OPTIONS $DEV/tests/$2/$1.py"
echo $COMMAND
echo $COMMAND >>$LOG
# Note all PyInstaller logged output goes to stderr
# I find no way in bash to append both stderr and stdout to a file
# in one command except by inserting a piped cat step as follows
exec $COMMAND 2>&1 | cat >>$LOG
#
# get a recursive file list of $DIST, sort and append to log
#
echo $DIVIDER "files in $DIST" $DIVIDER >>$LOG
find $DIST | sort >>$LOG
#
# append the contents of the executable, if it exists
# if --onedir, $DIST/$1/$1 is executable
# if --onfile, $DIST/$1 is it
# if a failure, doesn't exist at all
#
EXE=
if [ -e $DIST ] ; then
    # at least the dist dir was made
    if [ -d $DIST/$1 ] ; then
        # not one-file mode, $DIST/$1 is a folder
        if [ -e $DIST/$1/$1 ] ; then
            # a --onedir executable was made
            EXE="$DIST/$1/$1"
        fi
    elif [ -r $DIST/$1 ] ; then
        # a --onefile executable, probably
        EXE="$DIST/$1"
    fi
fi
if [ "x$EXE" != "x" ] ; then
    echo $DIVIDER "archive contents of $EXE" $DIVIDER >>$LOG
    echo 'o out00-PYZ.pyz
q
' | python $ARCHIVE_VIEWER $EXE >>$LOG
    echo $DIVIDER "Execution output of $EXE" $DIVIDER >>$LOG
    $EXE 2>&1 | cat >>$LOG
fi

PYTHONPATH=$ORIGINAL_PYTHONPATH
export PYTHONPATH