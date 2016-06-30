#!/usr/bin/env bash
set -e

find . -name '*.pyc' -delete

envsubst '$PY_VERSION' <Dockerfile.tmpl > Dockerfile

docker build -t pyinstaller .

docker run --rm -i \
    -e PIP_ACCEL_LOG_FORMAT \
    -v $HOME/.cache/pip:/root/.cache/pip \
    -v $HOME/.pip-accel:/var/cache/pip-accel \
    pyinstaller bash - <<EOF
        set -e
        (cd bootloader && python waf distclean all --no-lsb)
        pip install -e . | cat
        pip install pip-accel | cat
        pip-accel install -r tests/requirements-tools.txt | cat
        pip-accel install -r tests/requirements-linux.txt | pv -ft -i 60
        py.test -n 5 --maxfail 3 tests/unit/ tests/
EOF
