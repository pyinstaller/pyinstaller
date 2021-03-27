
pyenv and PyInstaller
=============================

.. TODO: finalize this section

.. note::
   This section is a still a draft.
   Please :ref:`help extending it <writing documentation>`.


* clone pyenv repository::

    git clone https://github.com/yyuu/pyenv.git ~/.pyenv

* clone virtualenv plugin::

    git clone https://github.com/yyuu/pyenv-virtualenv.git \
              ~/.pyenv/plugins/pyenv-virtualenv

* add to `.bashrc` or `.zshrc`::

    # Add 'pyenv' to PATH.
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"

    # Enable shims and autocompletion for pyenv.
    eval "$(pyenv init -)"
    # Load pyenv-virtualenv automatically by adding
    # # the following to ~/.zshrc:
    #
    eval "$(pyenv virtualenv-init -)"

* Install python version with shared libpython (necessary for PyInstaller to
  work)::

    env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.5.0

* setup virtualenv ``pyenv virtualenv 3.5.0 venvname``
* activate virtualenv ``pyenv activate venvname``
* deactivate virtualenv ``pyenv deactivate``

.. include:: ../_common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
