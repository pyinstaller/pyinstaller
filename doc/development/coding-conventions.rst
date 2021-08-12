.. _Coding conventions:

Coding conventions
===========================

The |PyInstaller| project follows the :pep:`8` Style Guide for Python Code for
new code.
It uses yapf_ to do the bulk of the formatting (mostly putting spaces in the
correct places) automatically and flake8_ to validate :pep:`8` rules which yapf_
doesn't cover.

Before submitting changes to |PyInstaller|, please check your code with both
tools.

To install them run::

    pip install flake8 yapf==0.31.0 toml

Reformat your code automatically with yapf_::

    yapf -rip .

Then manually adjust your code based on any suggestions given by flake8_::

    git diff -U0 last-commit-id-which-you-did-not-write -- | flake8 --diff -


Please abstain from reformatting existing code, even it it doesn't follow
PEP 8. We will not accept reformatting changes since they make it harder to
review the changes and to follow changes in the long run. For a complete
rationale please see :issue:`2727`.

.. include:: ../_common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
