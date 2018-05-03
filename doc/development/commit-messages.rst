
.. _Guidelines for Commits:

=============================
Guidelines for Commits
=============================

**Please help keeping code and changes comprehensible for years.
Provide a readable commit-history following this guideline.**

A commit

* stands alone as a single, complete, logical change,

* has a descriptive commit message (see :ref:`below <commit messages>`),

* has no extraneous modifications (whitespace changes,
  fixing a typo in an unrelated file, etc.),

* follows established coding conventions (:pep:`8`) closely.

Avoid committing several unrelated changes in one go. It makes merging
difficult, and also makes it harder to determine which change is the culprit
if a bug crops up.

If you did several unrelated changes before committing, ``git gui`` makes
committing selected parts and even selected lines easy. Try the context menu
within the windows diff area.

This results in a more readable history, which makes it easier to understand
why a change was made. In case of an issue, it's easier to `git bisect` to
find breaking changes any revert those breaking changes.


In Detail
====================

A commit should be one (and just one) logical unit.
It should be something that someone might want to patch or
revert in its entirety, and never piece-wise.
If it could be useful in pieces, make separate commits.

* Make small patches (i.e. work in consistent increments).

* Reformatting code without functional changes will generally not be
  accepted (for rationale see :issue:`2727`).
  If such changes are required, separate it into a commit of its own
  and document as such.

  This means
  that when looking at patches later, we don't have to wade through loads of
  non-functional changes to get to the relevant parts of the patch.

* Especially don't mix different types of change, and put a standard prefix
  for each type of change to identify it in your commit message.

* Abstain refactorings!
  If any, restrict refactorings (that should not change functionality) to
  their own commit (and document).

* Restrict functionality changes (bug fix or new feature) to their own
  changelists (and document).

* If your commit-series includes any "fix up" commits
  ("Fix typo.", "Fix test.", "Remove commented code.")
  please use ``git rebase -i …`` to clean them up
  prior to submitting a pull-request.

* Use ``git rebase -i`` to sort, squash, and fixup commits
  prior to submitting the pull-request.
  Make it a readable history, easy to understand what you've done.


.. _commit messages:

===================================
Please Write Good Commit Messages
===================================

**Please help keeping code and changes comprehensible for years.
Write good commit messages following this guideline.**

Commit messages should provide enough information to enable a third party to
decide if the change is relevant to them and if they need to read the change
itself.

|PyInstaller| is maintained since 2005 and we often need to
comprehend years later why a certain change has been implemented as it is.
What seemed to be obvious when the change was applied may be just obscure
years later. The original contributor may be out if reach, while another
developer needs get comprehend the reasons, side-effects and decisions the
original author considered.

We learned that commit messages are important to comprehend changes and
thus we are a bit picky about them.

We may ask you to reword your commit messages. In this case, use ``git
rebase -i …`` and ``git push -f …`` to update your pull-request. See
:ref:`updating pull-request` for details.


Content of the commit message
==================================

**Write meaningful commit messages.**

* The first line shall be a short sentence
  that can stand alone as a short description of the change,
  written in the present tense, and
  prefixed with the :ref:`subsystem-name <commit message standard prefixes>`.
  See :ref:`below <commit message first line>` for details.

* The body of the commit message should explain or justify the change,
  see :ref:`below <commit message body>`  for details.

Examples of good commit messages are
:commit:`5c1628e66e18e2bb1c44faa88387b1f627181b43` or
:commit:`73d7710613e26c3d59212e9e031f41a916c1e892`.


.. _commit message first line:

The first Line
=====================

The first line of the commit message shall

* be a short sentence (≤ 72 characters maximum, but shoot for ≤ 50),

* use the present tense ("Add awesome feature.") [#]_,

* be prefixed with an identifier for the
  :ref:`subsystem <commit message standard prefixes>`
  this commit is related to
  ("tests: Fix the frob." or "building: Make all nodes turn faster."),

* always end with a period.

* Ending punctuation other than a
  period should be used to indicate that the summary line is incomplete and
  continues after the separator; "..." is conventional.

.. [#] Consider these messages as the instructions for what applying the
  commit will do. Further this convention matches up with commit messages
  generated by commands like git merge and git revert.


.. _commit message body:

The Commit-Message Body
==================================

The body of a commit log should:

* explain or justify the change,

  - If you find yourself describing implementation details, this most probably
    should go into a source code comment.

  - Please include motivation for the change, and contrasts its
    implementation with previous behavior.

  - For more complicate or serious changes please document relevant decisions,
    contrast them with other possibilities for chosen,
    side-effect you experienced,
    or other thinks to keep in mind when touching this peace of code again.
    (Although the later *might* better go into a source code comment.)

* for a bug fix, provide a ticket number or link to the ticket,

* explain what changes were made at a high level
  (`The GNU ChangeLog
  <https://www.gnu.org/prep/standards/html_node/Change-Logs.html#Change-Logs>`_
  standard is worth a read),

* be word-wrapped to 72 characters per line, don't go over 80; and

* separated by a blank line from the first line.

* Bullet points and numbered lists are okay, too::

   * Typically a hyphen or asterisk is used for the bullet, preceded by a
     single space, with blank lines in between, but conventions vary here.

   * Use a hanging indent.

* Do not start your commit message with a hash-mark (``#``) as git some git
  commands may dismiss these message. (See `this discussion
  <http://stackoverflow.com/questions/2788092/start-a-git-commit-message-with-a-hashmark>`_.
  for details.)


.. _commit message standard prefixes:

Standard prefixes
========================

Please state the "subsystem" this commit is related to as a prefix in the
first line. Do learn which prefixes others used for the files you changed you
can use ``git log --oneline path/to/file/or/dir``.

Examples for "subsystems" are:

* ``Hooks`` for hook-related changes

* ``Bootloader``, ``Bootloader build`` for the bootloader or it's build system

* ``depend`` for the dependency detection parts (:file:`PyInstaller/depend`)

* ``building`` for the building part (:file:`PyInstaller/building`)

* ``compat`` for code related to compatibility of different Python versions
  (primary :file:`PyInstaller/compat.py`)

* ``loader``

* ``utils``, ``utils/hooks``

* ``Tests``, ``Test/CI``: For changes to the test suite (incl. requirements),
  resp. the CI.

* ``modulegraph``: changes related to :file:`PyInstaller/lib/modulegraph`

* ``Doc``, ``Doc build`` for the documentation content resp. it's build
  system. You may want to specify the chapter or section too.


Please set the correct Author
====================================

.. highlight: bash

Please make sure you have setup git to use the correct name and email for your
commits. Use the same name and email on all machines you may push from.
Example::

  # Set name and email
  git config --global user.name "Firstname Lastname"
  git config --global user.email "your_email@youremail.com"

This will set this name and email-address to be used for all git-repos you are
working on on this system. To set it for just the PyInstaller repo, remove the
``--global`` flag.

Alternatively you may use :command:`git gui` :menuselection:`--> Edit -->
Options ...` to set these values.


Further Reading
=======================

Further hints and tutorials about writing good commit messages can also be
found at:

* `FreeBSD Committer's Guide
  <http://www.freebsd.org/doc/en_US.ISO8859-1/articles/committers-guide/article.html>`_

* http://365git.tumblr.com/post/3308646748/writing-git-commit-messages

* http://wincent.com/blog/commit-messages: The Good, the Bad and the Ugly.

* http://wiki.scummvm.org/index.php/Commit_Guidelines

* http://lbrandy.com/blog/2009/03/writing-better-commit-messages/

* http://blog.looplabel.net/2008/07/28/best-practices-for-version-control/

* http://subversion.apache.org/docs/community-guide/conventions.html (Targeted
  a bit too much to subversion usage, which does not use such fine-grained
  commits as we ask you strongly to use.)

Credits
=========================

This page was composed from material found at

* http://hackage.haskell.org/trac/ghc/wiki/WorkingConventions/Git

* http://lbrandy.com/blog/2009/03/writing-better-commit-messages/

* http://365git.tumblr.com/post/3308646748/writing-git-commit-messages

* http://www.catb.org/esr/dvcs-migration-guide.html

* https://git.dthompson.us/presentations.git/tree/HEAD:/happy-patching

* and other places.


.. include:: ../_common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
