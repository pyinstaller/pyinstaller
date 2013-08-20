=======================
Testing PyInstaller
=======================

The test wokflow is not yet documented, but:

 * If those tests will be interactive (user has to click on a button),
   then it should go into `./tests/interactive/`, test for hooks (and
   suchlike) go into `./tests/libraries/`. If you are working on a
   core function, `./tests/basic/` or `./tests/import/` are
   appropriate.

 * If you have more test files, create them with file name prefix
   ``test_yourtest_``.

 * To run all tests::

    cd tests
    python runtests.py

 * To run a single test::

    cd tests
    python runtests.py libraries/test_yourtest

 * To run all interactive tests::

    cd tests
    python runtests.py -i

 * Test success depends on zero exit status of created binary.


For more information pleas see
http://www.pyinstaller.org/wiki/Development/HowtoContribute.

..
  Local Variables:
  mode: rst
  ispell-local-dictionary: "american"
  End:
