#!/bin/bash
pushd bootloader
docker build -f Dockerfile-i386 -t gc/pyinstaller_bootloader32 .
docker build -f Dockerfile-amd64 -t gc/pyinstaller_bootloader64 .
popd
docker run -v "$(pwd):/src" --name bootloader32 gc/pyinstaller_bootloader32
docker run -v "$(pwd):/src" --name bootloader64 gc/pyinstaller_bootloader64
docker rm bootloader32
docker rm bootloader64
docker rmi gc/pyinstaller_bootloader32
docker rmi gc/pyinstaller_bootloader64
