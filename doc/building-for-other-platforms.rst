.. _building for other platforms:

Building Cross Platform
=======================

PyInstaller is not a cross compiler. Due to Python's dynamic nature, PyInstaller
needs to run snippets of code from the target Python environment at build time
and it can only do that if said environment is runable on (i.e. built for) the
current platform. Hence, PyInstaller ever becoming a cross compiler is
impossible.

However, building for platforms you don't own is still possible through use of
either virtualisation or *Continuous Integration* (a.k.a. CI/CD). These are in
fact much better than cross compiling since you can also use them to verify your
application rather than relying on your users to tell you that your
application's defunct.


Virtualisation
~~~~~~~~~~~~~~


Building for Linux
------------------


.. code-block:: bash

    docker run -it -v "$PWD:/io" ubuntu:20.04
    cd /io
    export LANG=C.UTF-8 LC_ALL=C LANGUAGE=C DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install --no-install-recommends -y software-properties-common curl binutils
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update
    apt-get install --no-install-recommends -y libpython3.11 python3.11
    pip install pyinstaller -r requirements.txt
    python3.11 your-code.py
    pyinstaller application.py
    ./dist/application/application


.. warning:

    Never distribute an application built using WSL or on a modern OS without
    containers. Your GLIBC version will be high making your application unlikely
    to work on all but the very newest of target machines.


Building for Linux cross architecture
-------------------------------------




Building for macOS x86_64
-------------------------




Building for macOS arm64
------------------------


Building for Windows AMD64 (a.k.a. 64 bit)
------------------------------------------




Building for Windows x86 (a.k.a. 32 bit)
----------------------------------------

To build for 32 bit, simply use a 32 bit Python installer from
`python.org/downloads <https://python.org/downloads>`_ on any (virtualised)
Windows platform. Pip will automatically ensure that you get 32 bit variants of
PyInstaller and all of your dependencies.


Building for Windows ARM64
--------------------------

All Windows ARM64 devices can use emulation to run x86 binaries and almost all
can run AMD64 binaries so if performance isn't critical, building either of
those is acceptable. Note that not many packages support Windows ARM64 which may
force you to take the emulation route even if you can access ARM64 hardware.


.. _deadsnakes: https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa
.. _UTM: https://mac.getutm.app/
.. _UTM Windows: https://docs.getutm.app/guides/windows/



.. _supporting older platforms:

Supporting older platforms
~~~~~~~~~~~~~~~~~~~~~~~~~~


Windows
-------

To support Windows 7, 8.0 or server <= 2012, you must use Python 3.8 or older
since Python itself dropped support for these platforms.


macOS
-----

On macOS, the macOS deployment target of all your binaries must be <= the
oldest version of macOS you intend to support. This means:

- You can't use anything from Homebrew (Python itself, Python packages,
  command line tools, Dylibs).

- When compiling anything from source, clang must be given the
  ``-mmacosx-version-min=10.14`` flag. If the version of macOS you're
  targeting is less than 10.12 then clang also needs the
  ``-Wunguarded-availability`` and ``-Werror=unguarded-availability`` flags.
  Depending on the build system, this is usually controlled by setting the
  ``MACOSX_DEPLOYMENT_TARGET=10.14`` environment variable.


Linux
-----


