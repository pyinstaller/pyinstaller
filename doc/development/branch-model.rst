.. _branch model:

|PyInstaller|'s Branch Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:`develop` branch: We consider `origin/develop` to be the main branch where the
  source code of HEAD always reflects a state with the latest delivered
  development changes for the next release. Some would call this the
  “integration branch”.

:`master` branch: We consider `origin/master` to be the main branch where the
  source code of HEAD always reflects a *production-ready* state. Each commit
  to master is considered a new release and will be tagged.

The |PyInstaller| project doesn't use long living branches (beside `master`
and `develop`) as we don't support bugfixes for several major releases in
parallel.

Occasionally you might find these branches in the repository: [#]_

:`release/` branches: These branches are for preparing the next release. This
  is for example: updating the version numbers, completing the change-log,
  recompiling the bootloader, rebuilding the manuals.
  See ref:`release-workflow` for details about the release process and what
  steps have to be performed.

:`hotfix/` branches: These branches are also meant to prepare for a new
  production release, albeit unplanned.
  This is what is commonly known as a "hotfix".

:`feature/` branches: Feature branches (or sometimes called topic branches)
  are used to develop new features for the upcoming or a distant future
  release.


.. [#] This branching-model is basically the same as `Vincent Driessen
   described <http://nvie.com/posts/a-successful-git-branching-model/>`_ in
   this blog. But currently we are not following it strictly.


.. include:: ../_common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
