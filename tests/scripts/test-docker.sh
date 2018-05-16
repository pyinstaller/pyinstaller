#!/bin/bash -ex

_args="py.test -n8 tests/functional"
if [[ -n $1 ]]; then
    _args=$@
fi

_image="pyinstaller-functional-tests"
docker build -t ${_image} -f "$(dirname $0)/Dockerfile" .
docker run -it -v "$(pwd):/src" --rm ${_image} ${_args}
