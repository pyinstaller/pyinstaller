#!/usr/bin/env bash
set -e

find . -name '*.pyc' -delete

envsubst '$PY_VERSION' <Dockerfile.tmpl > Dockerfile

echo 'building pyinstaller image'
docker build --pull -t pyinstaller .

echo 'creating pyinstaller container'
2>/dev/null docker rm -v pyinstaller || true
docker create -i --name pyinstaller \
    -e PIP_ACCEL_LOG_FORMAT \
    pyinstaller bash -

trap 'docker rm -v pyinstaller' EXIT

echo 'initializing container cache dirs'
docker start -i pyinstaller < <(echo 'mkdir -p /root/.cache/pip /var/cache/pip-accel')

echo 'loading pip cache'
docker cp $HOME/.cache/pip/ pyinstaller:/root/.cache/

echo 'loading pip-accel cache'
docker cp $HOME/.pip-accel/. pyinstaller:/var/cache/pip-accel/

docker start -i pyinstaller <<EOF
    set -e
    (cd bootloader && python waf distclean all --no-lsb)

    echo 'installing pyinstaller'
    pip install -e . | cat

    echo 'installing pip-accel'
    pip install pip-accel | cat

    echo 'installing requirements-tools'
    pip-accel install -r tests/requirements-tools.txt | cat

    echo 'installing requirements-linux'
    pip-accel install -r tests/requirements-linux.txt | pv -ft -i 60

    echo 'running tests'
    # py.test -n 5 --maxfail 3 tests/unit/ tests/
EOF

echo 'extracting pip cache'
docker cp pyinstaller:/root/.cache/pip/ $HOME/.cache/

echo 'extracting pip-accel cache'
docker cp pyinstaller:/var/cache/pip-accel/. $HOME/.pip-accel/
