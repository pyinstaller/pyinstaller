
.. _writing documentation:

============================================
Improving and Building the Documentation
============================================

|PyInstaller|'s documentation is created using Sphinx_.
Sphinx uses reStructuredText_ as its markup language, and many of its
strengths come from the power and straightforwardness of reStructuredText and
its parsing and translating suite, Docutils_.

.. _reStructuredText: http://docutils.sourceforge.net/rst.html
.. _Sphinx: http://www.sphinx-doc.org/
.. _Docutils: http://docutils.sourceforge.net/

The documentation is maintained in the Git repository along with the code
and pushing to the ``develop`` branch will create
a new version at https://pyinstaller.readthedocs.io/en/latest/.


For **small changes** (like typos) you may just fork |PyInstaller| on Github,
edit the documentation online and create a pull-request.

For anything else we ask you to clone the repository and verify your changes
like this::

  pip install -r doc/requirements.txt
  cd doc
  make html
  xdg-open _build/html/index.html


Please watch out for any warnings and errors while building the documentation.
In your browser check if the markup is valid
prior to pushing your changes and creating the pull-request.
Please also run::

  make clean
  ...
  make html

to verify once again everything is fine. Thank you!


We may ask you to rework your changes or reword your commit messages. In this
case, use ``git rebase -i …`` and ``git push -f …`` to update your
pull-request. See :ref:`updating pull-request` for details.


|PyInstaller| extensions
----------------------------

For the |PyInstaller| documentation there are roles available [*]_
in additon to the ones from `Sphinx`__ and docutils__.

__ http://www.sphinx-doc.org/en/stable/markup/inline.html
__ http://www.sphinx-doc.org/en/stable/rest.html#inline-markup

.. rst:role:: commit

   Refer to a commit, creating a web-link to the online git repository.
   The commit-id will be shortened to 8 digits for readability. 
   Example: ``:commit:`a1b2c3d4e5f6a7b8c9``` will become
   :commit:`a1b2c3d4e5f6a7b8c9`.

.. rst:role:: issue

   Link to an issue or pull-request number at Github.
   Example: ``:issue:`123``` will become :issue:`123`.


.. [*] Defined in :file:`doc/_extensions/pyi_sphinx_roles.py`


reStructuredText Cheat-sheet
---------------------------------------

* Combining markup and links::

    The easies way to install PyInstaller is using |pip|_::

    .. |pip| replace:: :command:`pip`
    .. _pip: https://pip.pypa.io/


.. include:: ../_common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
