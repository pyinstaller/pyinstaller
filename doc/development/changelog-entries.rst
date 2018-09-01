.. _changelog entries:


Changelog Entries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your change is noteworthy, there needs to be a changelog entry so our users
can learn about it!

To avoid merge conflicts, we use the towncrier_ package to manage our
changelog. ``towncrier`` uses independent files for each pull request --
called *news fragments* -- instead of one monolithic changelog file. On
release, those news fragments are compiled into our ``doc/CHANGELOG.rst``.

You don't need to install ``towncrier`` yourself, you just have to abide by a
few simple rules:

* For each pull request, add a new file into `news/` with a filename
  adhering to the ``pr#.(feature|bugfix|breaking).rst`` schema:
  For example, :file:`news/42.feature.rst` for a new feature that is
  proposed in pull request #42.

  Our categories are:
  ``feature``,
  ``bugfix``,
  ``break`` (breaking changes),
  ``hooks`` (all hook-related changes),
  ``bootloader``,
  ``moduleloader``,
  ``doc``,
  ``process`` (project infrastructure, development process, etc.=,
  ``core``,
  ``build`` (the bootloader build process),
  and
  ``tests``.


* As with other docs, please use `semantic newlines`_ within news fragments.

* Prefer present tense or constructions with "now" or "new".
  For example:

  - Add hook for my-fancy-library.
  - Fix crash when trying to add resources to Windows executable using
    ``--resource`` option.

  If the change is relavant only fo a specific platform, use a prefix,
  like here:

  - (GNU/Linux) When building with ``--debug`` turn of FORTIFY_SOURCE to ease
    debugging.

* Wrap symbols like modules, functions, or classes into double backticks so
  they are rendered in a monospace font.
  If you mention functions or other callables, add parentheses at the end of
  their names: ``is_module()``.
  This makes the changelog a lot more readable.

* If you want to reference multiple issues,
  copy the news fragment to another filename.
  ``towncrier`` will merge all news fragments with identical contents
  into one entry with multiple links to the respective pull requests.
  You may also reference to an existing newsfragment by copying that one.

* If your pull-request includes several distinct topics, you may want to add
  several news fragment files.
  For example
  ``4242.feature.rst`` for the new feature,
  ``4242.bootloader`` for the accompanying change to the bootloader.

Remember that a news entry is meant for end users
and should only contain details relevant to an end user.

.. _semantic newlines: http://rhodesmill.org/brandon/2012/one-sentence-per-line/


.. include:: ../_common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
