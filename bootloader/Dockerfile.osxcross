# This is osxcross-based container for cross-compiling the bootloader
# for macOS.
#
# Build instructions:
#
# 1. Download the "Command Line Tools for XCode" package from
#   https://developer.apple.com/download/more
# This requires Apple ID, which you can obtain by registering for free.
#
# 2. In this directory (i.e., pyinstaller/bootloader), create _sdks/macos
# directory, and copy the downloaded Command_Line_Tools_for_Xcode_12.5.dmg
# to _sdks/macos/Command_Line_Tools_for_Xcode.dmg (i.e., remove the
# version from the filename).
#
# 3. Build the container:
#   docker build -f Dockerfile.osxcross -t pyi-osxcross --build-arg "SDK_VERSION=11.3"
#
# The SDK_VERSION must match the MacOS SDK version provided by the Tools
# package. If the package provides a single version of MacOS SDK, it may
# be omitted. If multiple versions are provided and SDK_VERSION is not
# specified, the toolchain build script will terminate with error message
# that SDK_VERSION needs to be set. The version must be provided in
# major.minor format (e.g., 11.3 or 10.15). For list of MacOS SDK versions
# available in each XCode release, see:
#  https://en.wikipedia.org/wiki/Xcode#12.x_series
# For example, Command Line Tools for XCode 12.5 provides MacOS SDK 11.3
# (as well as 10.15).
#
# Optional MACOSX_DEPLOYMENT_TARGET build argument can be used to set
# deployment target version of bootloaders. By default, it is set to
# 10.13.
#
# The build process might take a while.
#
# Usage:
#
# Once the container has been built, it can be ran from this directory
# (i.e., pyinstaller/bootloader) as:
#   docker run --rm -v "$PWD/..:/io" -t pyi-osxcross
# or from PyInstaller top-level source directory as:
#   docker run --rm -v "$PWD:/io" -t pyi-osxcross


########################################################################
#                  Build the cross-compile toolchain                   #
########################################################################
FROM fedora:34 AS builder

# Install packages required by osxcross
RUN dnf install -y \
    findutils \
    git \
    cmake \
    clang \
    llvm-devel \
    libxml2-devel \
    libuuid-devel \
    openssl-devel \
    bash \
    patch \
    libstdc++-static \
    make \
    xz \
    cpio \
    bzip2-devel

# Check out the osxcross repo
WORKDIR /tmp/osxcross-build
RUN git clone --depth 1 https://github.com/tpoechtrager/osxcross.git .

# SDK version to use. Required if multiple versions are provided by the
# "Command Line Tools for XCode" package.
ARG SDK_VERSION

# Extract MacOSX SDK(s) from Command Line Tools for Xcode package.
# This assumes we are building from within pyinstaller/bootloader directory.
COPY ./_sdks/macos/Command_Line_Tools_for_Xcode.dmg /tmp/tools.dmg
RUN ./tools/gen_sdk_package_tools_dmg.sh /tmp/tools.dmg && mv MacOSX*.tar.* tarballs/

# Build the toolchain
ENV UNATTENDED=1
RUN ./build.sh


########################################################################
#                        The actual compiler VM                        #
########################################################################
FROM fedora:34

# Install packages
RUN dnf install -y python3 clang

# Copy cross-compilation toolchain from the builder container
COPY --from=builder /tmp/osxcross-build/target /opt/osxcross

# Set paths
ENV PATH=/opt/osxcross/bin:$PATH
ENV LD_LIBRARY_PATH=/opt/osxcross/lib:$LD_LIBRARY_PATH

# Set macOS deployment target - 10.13 by default, but can be overridden
# at container build time.
ARG MACOSX_DEPLOYMENT_TARGET=10.13

# Build the bootloader
# The PyInstaller top source directory must be mounted as a volume to
# /io when the image is run, e.g.:
# docker run -v "/path/to/pyinstaller:/io" <image_name>
WORKDIR /io/bootloader
# Resolve clang and strip binaries
CMD CC=$(basename -a /opt/osxcross/bin/x86_64-*-clang) STRIP=$(basename -a /opt/osxcross/bin/x86_64-*-strip) python3 ./waf configure all --clang
