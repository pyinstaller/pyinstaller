[tox]
envlist = py24,py25,py26,py27
toxworkdir=/tmp/tox

[testenv]
sitepackages=True
;deps= -rtests/test-requirements.txt
setenv =
    PYTHONPATH =
changedir=tests
commands=
    ./runtests.py []
    ./runtests -c

