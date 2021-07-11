# A dockcross image with a cross compiled version of zlib installed.
#
# This dockerfile can be used to (cross)compile PyInstaller's Linux bootloaders
# for any architecture supported by dockcross.
#
# Usage:
# ------
#
# Building the bootloaders is two-part. First you need to build the docker
# image (or "build the builder") before you can compile any bootloaders.
# YOU MUST BE CD-ed IN THE ROOT OF THIS REPOSITORY DURING BOTH STAGES.
#
# Build the image:
#
#   Build the default of x86_64 architecture:
#
#       docker build -t bob-the-build-image ./bootloader
#
#   (Note that bob-the-build-image is just an arbitrary name.)
#
#   Specify an different architecture by using an alternative base image from
#   https://hub.docker.com/u/dockcross with --build-arg BASE=[image].
#   e.g. To build for aarch64 (a.k.a armv8l) use the aarch64 manylinux base:
#
#      docker build --build-arg BASE=dockcross/manylinux2014_aarch64 -t bob-the-build-image ./bootloader
#
# Build the bootloaders:
#
#   Simply run:
#
#     docker run -v "$PWD:/io" -t bob-the-build-image
#
#   The bootloaders should appear in the PyInstaller/bootloader/[platform]
#   directory.
#

ARG BASE=dockcross/manylinux2014-x64
FROM ${BASE}

ARG ZLIB_VERSION=1.2.11

# Download and unpack zlib somewhere out the way.
WORKDIR /home/
RUN wget https://zlib.net/zlib-${ZLIB_VERSION}.tar.gz \
    && tar xf zlib-$ZLIB_VERSION.tar.gz && rm zlib-$ZLIB_VERSION.tar.gz

WORKDIR zlib-$ZLIB_VERSION
# Install zlib-devel but in the sysroot of the cross compiler.
RUN ./configure --prefix="$($CC -print-sysroot)"
RUN make
RUN make install

WORKDIR /io
# Redefine the C compiler so that works.
# Because this compiler is so old, C99 features need to be explicitly enabled
# and PATH_MAX needs to be manually defined. -std=c99 truly means strict
# posix C99 compliance which disables the non-posix symbols like seeko() which
# we use for huge files. The last define re-enables them.
ENV CC="$CC -std=c99 -D PATH_MAX=1024 -D_POSIX_C_SOURCE=200808L"

# Set building the bootloader as the default run command.
CMD cd bootloader && ./waf all
