# Setup an Ubuntu test environment with Python, PyInstaller and its test dependencies.
#
# To build, boot into and invoke pytest inside this image run:
#
#   docker build -f ubuntu3_9.dockerfile -t ubuntu3_9 .
#   docker run -it ubuntu3_9
#   pytest
#
# Or if you prefer a one-liner:
#
#   docker run -it $(docker build -q -f ubuntu3_9.dockerfile .) pytest
#
# This docker file should be used for testing only. The bootloaders it compiles internally are not suitable for PyPI.
#
# ---
# This dockerfile is 2-part. The first half builds and the second tests. The test half should only contain PyInstaller's
# runtime and test dependencies - no C compiler or dev packages. Once other packages start shipping musl compatible
# wheels, most or possibly all of the build half will be safely removable.

FROM ubuntu:22.04 as wheel-factory
RUN apt-get update && apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt update && DEBIAN_FRONTEND=noninteractive apt install -y python3.9 python3.9-dev python3.9-distutils
RUN echo '#!/bin/bash\npython3.9' > /usr/bin/python && \
    chmod a+x /usr/bin/python
RUN apt install -y curl
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.9

# Install a C compiler.
RUN apt install -y musl-dev gcc
# With zlib headers to compiler the bootloader,
RUN apt install -y zlib1g-dev
# Linux headers to build psutil from source.
RUN apt install -y linux-headers-generic


# Build/download wheels for all test requirements.
RUN mkdir -p /io/tests
WORKDIR /io
COPY tests/requirements-base.txt tests/
COPY tests/requirements-tools.txt tests/
RUN pip wheel -r tests/requirements-tools.txt -w wheels


# Build a wheel for PyInstaller. Do this last and use as few files as possible to maximize cache-ability.
COPY COPYING.txt .
COPY setup.* ./
COPY bootloader bootloader
COPY PyInstaller PyInstaller
RUN python3.9 setup.py -qqq bdist_wheel -d wheels


FROM ubuntu:22.04
RUN apt-get update && apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt update && DEBIAN_FRONTEND=noninteractive apt install -y python3.9 python3.9-dev python3.9-distutils
RUN echo '#!/bin/bash\npython3.9' > /usr/bin/python && \
    chmod a+x /usr/bin/python
RUN apt install -y curl
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.9

CMD "/bin/bash"
WORKDIR /io

# Runtime libraries required by lxml.
RUN  apt install -y libxml2-dev libxslt1-dev
# Required by tkinter.
RUN apt install -y python3.9-tk
# Used as a test library for some ctypes finding tests.
RUN apt install -y libpng-dev
# And by PyInstaller itself.
RUN apt install -y binutils

COPY setup.cfg .

# Import and the precompiled wheels from the `build` image.
COPY --from=wheel-factory /io/wheels /wheels
RUN pip install /wheels/*.whl

COPY tests /io/tests
