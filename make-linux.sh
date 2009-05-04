#!/bin/bash
echo "USAGE $0 some-python-version"
cd source/linux && $1 Make.py && make clean && make && cd -

