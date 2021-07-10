.. _creating pull-requests:

======================
Creating Pull-Requests
======================

.. highlight: bash

Example
-------

* Create an account on https://github.com

* Create a fork of project `pyinstaller/pyinstaller
  <https://github.com/pyinstaller/pyinstaller/>`_ on github.

* Set up your git client by following `this documentation on github
  <http://help.github.com/set-up-git-redirect>`_.

* Clone your fork to your local machine.::

    git clone git@github.com:YOUR_GITHUB_USERNAME/pyinstaller.git
    cd pyinstaller

* Develop your changes (aka "hack")

  * Create a branch to work on (optional)::

      git checkout -b my-patch

  * If you are going to implement a hook, start with creating a minimalistic
    build-test (see below). You will need to test your hook anyway, so why not
    use a build-test from the start?

  * Incorporate your changes into |PyInstaller|.

  * Test your changes by running *all* build tests to ensure nothing else is
    broken. Please test on as many platform as you can.

  * You may reference relevant issues in commit messages (like #1259) to make
    GitHub link issues and commits together, and with phrase like “fixes #1259”
    you can even close relevant issues automatically.

* Synchronize your fork with the PyInstaller upstream repository. There are two
  ways for this:

  1. Rebase you changes on the current development head (preferred, as it
     results in a straighter history and conflicts are easier to solve)::

      git remote add upstream https://github.com/pyinstaller/pyinstaller.git
      git checkout my-patch
      git pull --rebase upstream develop
      git log --online --graph

  2. Merge the current development head into your changes::

      git remote add upstream https://github.com/pyinstaller/pyinstaller.git
      git fetch upstream develop
      git checkout my-patch
      git merge upstream/develop
      git log --online --graph

  For details see `syncing a fork at github
  <https://help.github.com/articles/syncing-a-fork>`_.

* Push your changes up to your fork::

    git push

* Open the *Pull Requests* page at
  https://github.com/YOUR_GITHUB_USERNAME/pyinstaller/pulls
  and click “New pull request”.
  That’s it.


.. _updating pull-request:

Updating a Pull-Request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We may ask you to update your pull-request to improve it's quality or for
other reasons. In this case, use ``git rebase -i …`` and ``git push -f …`` as
explained below. [#]_ Please *do not* close the pull-request and open a new
one – this would kill the discussion thread.

This is the workflow without actually changing the base::

   git checkout my-branch
   # find the commit your branch forked from 'develop'
   mb=$(git merge-base --fork-point develop)
   # rebase interactively without actually changing the base
   git rebase -i $mb
   # … process rebase
   git push -f my-fork my-branch


Or if you want to actually base your code on the current development head::

   git checkout my-branch
   # rebase interactively on 'develop'
   git rebase -i develop
   # … process rebase
   git push -f my-fork my-branch


.. [#] There are other ways to update a pull-request, e.g. by "amending" a
   commit. But for casual (and not-so-casual :-) users ``rebase -i`` might be
   the easiest way.


.. include:: ../_common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
