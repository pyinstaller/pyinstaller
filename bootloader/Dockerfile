# A dockcross image with a cross compiled version of zlib installed.
#
# This dockerfile can be used to (cross)compile PyInstaller's Linux bootloaders for any architecture supported by
# dockcross.
#
# Usage:
# ------
#
# Building the bootloaders is two-part. First you need to build the docker image (or "build the builder") before you can
# compile any bootloaders. YOU MUST BE CD-ed IN THE ROOT OF THIS REPOSITORY DURING BOTH STAGES.
#
# Build the image:
#
#   Build the default of x86_64 architecture:
#
#       docker build -t bob-the-build-image ./bootloader
#
#   (Note that bob-the-build-image is just an arbitrary name.)
#
#   Specify an different architecture by using an alternative base image from https://hub.docker.com/u/dockcross or
#   https://quay.io/organization/pypa/ with --build-arg BASE=[image]. e.g. To build for aarch64 (a.k.a armv8l) use the
#   aarch64 manylinux base:
#
#      docker build --build-arg BASE=dockcross/manylinux2014_aarch64 -t bob-the-build-image ./bootloader
#
# Build the bootloaders:
#
#   Simply run:
#
#     docker run -v "$PWD:/io" -t bob-the-build-image
#
#   The bootloaders should appear in the PyInstaller/bootloader/[platform] directory.
#

ARG BASE=dockcross/manylinux2014-x64
FROM ${BASE}

ARG ZLIB_VERSION=1.2.11

# Download and unpack zlib.
WORKDIR /home/
RUN curl -s https://zlib.net/zlib-${ZLIB_VERSION}.tar.gz | tar xfz -

ENV CC=${CC:-gcc}

WORKDIR zlib-$ZLIB_VERSION
# Install zlib-devel but in the sysroot of the cross compiler.
RUN ./configure --prefix="$($CC -print-sysroot)"
RUN make
RUN make install

# Set the default Python to 3.9.
ENV PATH=/opt/python/cp39-cp39/bin:$PATH

WORKDIR /io

# Set building the bootloader as the default run command.
CMD cd bootloader && python3 ./waf all
