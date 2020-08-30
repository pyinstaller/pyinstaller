Add hook for distutils.util to not pull in lib2to3 unittests, which will be
rearly used in frozen packages.
