
New to GitHub or Git?
==========================

Our development workflow is build around Git and GitHub.
Please take your time to become familiar with these.
If you are new to GitHub,
`GitHub has instructions <https://help.github.com/categories/bootcamp/>`_
for getting you started.
If you are new to Git there are a
`tutorial <https://git-scm.com/docs/gittutorial>`_ and an
`excellent book available online <https://git-scm.com/book>`_.


.. _Guidelines for Commits:

Guidelines for Commits
=============================

* **Commit often and in logical chunks.**
  A commit should be one (and just one) logical unit. It should be something
  that someone might want to patch or revert in its entirety, and never
  piecewise. If it could be useful in pieces, make separate commits.

* **Write meaningful commit messages.**
  Using atomic commits will result in short, clear,
  and concise commit messages.
  Non-atomic commits make for awful run-on commit messages.

* Try to make small patches (i.e. work in consistent increments).

* Separate changes that affect functionality from those that just affect code
  layout, indendation, whitespace, filenames etc. This means that when looking
  at patches later, we don't have to wade through loads of non-functional
  changes to get to the important parts of the patch.

* Especially don't mix different types of change, and put a standard prefix
  for each type of change to identify it in your commit message.

* Restrict all whitespace changes to a specific type and document as such.

* Restrict refactorings (that should not change functionality) to their own
  commit (and document).

* Restrict functionality changes (bug fix or new feature) to their own
  changelists (and document).

* If possible, commit often. This helps to avoid conflicts.

* Only push when your tree passes validation: see TestingPatches.

* Discuss anything you think might be controversial before pushing it.


.. include:: ../_common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
