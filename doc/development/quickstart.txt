

Quick-start
=============================

* Our git repository is at https://github.com/pyinstaller/pyinstaller::

    git clone https://github.com/pyinstaller/pyinstaller

  - Development is done on the `develop` branch. Pull-request shall be filed
    against this branch.

  - Releases will reside on the `master` branch.

* Install required testing tools::

    pip install -r tests/requirements-tools.txt

* Commit as often as you’d like, but squash or otherwise
  rewrite your commits into logical patches before asking
  for code review. ``git rebase -i`` is your friend.
  Read the :ref:`»» Detailed Commit Guideline <Guidelines for Commits>`
  for more information.

  Reformatting code without functional changes will generally not be accepted
  (for rational see :issue:`2727`).

* Write meaningful commit messages.

  - The first line shall be a short sentence
    that can stand alone as a short description of the change,
    written in the present tense, and
    prefixed with the :ref:`subsystem-name <commit message standard prefixes>`.

  - The body of the commit message should explain or justify the change.
    Read the :ref:`»» Detailed Commit Message Rules <commit messages>`
    for more information.

* Provide tests that cover your changes and try to run the tests locally
  first.

* Submit pull-requests against the ``develop`` branch.
  Mind adding a :ref:`changelog entry <changelog entries>`
  so our users can learn about your change!

* For new files mind adding the copyright header, see
  |PyInstaller/init.py|_
  (also mind updating to the current year).

  .. |PyInstaller/init.py| replace:: :file:`PyInstaller/__init__.py`
  .. _PyInstaller/init.py: https://github.com/pyinstaller/pyinstaller/blob/develop/PyInstaller/__init__.py

* In response to feedback, squash the new "fix up" commits
  into the respective commit that is being fixed
  with an interactive rebase (``git rebase -i``). 
  :ref:`Push the new, rewritten branch <updating pull-request>`
  with a ``git push --force``.
  (Scary! But github doesn’t play nicely with a safer method.)


.. include:: ../_common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
