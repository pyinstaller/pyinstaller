Releasing PyInstaller
---------------------

*How to put PyInstaller on PyPI*


Prerequisites
.............

* It's assumed that you are running in a UNIX like environment with tools like
  ``bash`` and ``perl`` available.

* It's also assumed that your Python environment is suitably de-`xkcd-1987
  <https://xkcd.com/1987>`_-ified. i.e ``which python`` points to a sensible,
  non-EOL version of Python 3 with user-writable ``site-packages`` directory and
  ``which pip`` points to that same environment.

* You need to install and be running `fish <https://fishshell.com/>`_. (Just
  entering ``fish`` into a terminal is enough, no need to ``chsh``).

* You need ``docker`` with ``qemu`` (cross architecture emulation). These are
  typically just called ``docker`` and ``qemu`` on Linux repositories. Windows and
  macOS can get them via docker desktop. To test your setup run:

  .. code-block:: bash

      $ docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
      ... lots of noise ...
      $ docker run --rm --platform=ppc64le alpine uname -m
      ... some more noise ...
      ppc64le


To release PyInstaller to PyPI
..............................

The steps to do a release are below. Note that only explicitly typing the
commands ``pyi_upload_to_pypi`` or ``pyi_github_release`` or a ``git push`` will
make persistent online changes. All other steps are harmless in that they apply
changes locally only and can be undone by running ``git reset --hard
origin/develop``. It *should* be impossible to accidentally create a release or
other irreversible change just by monkeying around.

#.  Ensure that you are on the ``develop`` branch, your working directory is
    clean and you have pulled the latest upstream changes.

#.  ``cd`` to the root of this repo and enter fish:

    .. code-block:: bash

        $ fish

#.  Source the ``release.fish`` script.

    .. code-block:: fish

        > source release/release.fish

    That script should prompt you for everything you need to do from there on.

