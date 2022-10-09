#!/usr/bin/env fish

if not status is-interactive
    echo 'This script must be sourced from a fish shell' ; exit 1
end
for command in python pip git perl nano bash grep gh
    if not which $command > /dev/null 2>&1
        echo Missing dependency: Please install (set_color $fish_color_command)$command(set_color normal) and ensure it\'s in PATH before running this script.
        exit 1
    end
end

open https://readthedocs.org/projects/pyinstaller/builds/
if not test (read -n1 -P 'Are the most recent "version latest" readthedocs builds passing? (y/N) ') = y
    echo 'Do not attempt to do a release whilst readthedocs is in an unstable state! Create and merge a pull request to fix whatever\'s broken then restart the release process.'
    exit 1;
end

set -x PYINSTALLER_DO_RELEASE 1
pip install -q -r doc/requirements.txt
pip install -Uq twine

read -n1 -P 'nano is about to be opened so that you can edit PyInstaller\'s version. When it does, write the new version then save and quit. Press any key to proceed: '
nano +21 PyInstaller/__init__.py
towncrier --yes
sh -c 'cd doc && make man'

# Insert a section for this release into the credits file.
set header (head -n7 doc/CREDITS.rst)
set footer (tail -n +7 doc/CREDITS.rst)
printf '%s\n' $header > doc/CREDITS.rst
set title 'Contributions to PyInstaller '(python setup.py --version)
echo $title >> doc/CREDITS.rst
echo $title | perl -pe 's/./-/g' >> doc/CREDITS.rst
echo '' >> doc/CREDITS.rst
git shortlog -ns (git tag -l)[-1].. | grep -v -w bot | perl -pe 's/^\s+\d+\s+/* /g' >> doc/CREDITS.rst
printf '%s\n' $footer >> doc/CREDITS.rst

# Update docs versions in the README.
perl -pe 's&https?://pyinstaller.readthedocs.io&https://pyinstaller.org&g' -i README.rst
perl -pe 's&(https://pyinstaller.org/en/)[^/]+/&$1'v(python setup.py --version)'/&g' -i README.rst

sh -c 'cd doc; make clean html'
open doc/_build/html/CHANGES.html
open doc/_build/html/CREDITS.html
while not test (read -n1 -P 'Do the two opened docs pages look OK? Check for formatting/spelling errors. If yes, type \'y\', otherwise edit the rst source files then type anything else to trigger a rebuild: ') = y
    sh -c 'cd doc; make clean html'
end

read -P 'If the bootloaders need to be rebuilt, now is the time to do it. Hit return if they don\'t need rebuilding or once you have rebuilt and copied the '(set_color --bold)'Windows and macOS bootloaders only'(set_color normal)' into PyInstaller/bootloaders: '

echo 'Building bootloaders for Linux. If this is the first time you\'ve done so on this machine then this will take a while.'
./release/build-manylinux || exit 1

function pyi_build_wheels
    rm -rf build dist pyinstaller.egg-info
    python setup.py bdist_wheels
    python setup.py -qqq sdist
    twine check dist/* || return 1
end

function pyi_upload_to_pypi
    echo 'API tokens can be created at https://pypi.org/manage/account/token/'
    twine upload -u __token__ dist/*
end

function pyi_commit
    git add -u
    git commit -m 'Release v'(python setup.py --version)'. [skip ci]'
    git tag v(python setup.py --version)
    echo 'A commit and tag for this release has been made. When you\'re ready run:'
    echo -s '    ' (set_color $fish_color_command) 'git push; sleep 60; git push --tags' (set_color normal)
    echo 'Note that the dumb delay is required to avoid hitting readthedocs\'s concurrent build limit.'
end

function pyi_github_release
    gh release create v(python setup.py --version) --notes 'Please see the [v'(python setup.py --version)' section of the changelog](https://pyinstaller.org/en/v'(python setup.py --version)'/CHANGES.html#id1) for a list of the changes since '(git tag -l --sort=version:refname)[-2]'.'
end

printf 'Commands '
printf (set_color $fish_color_command)'%s'(set_color normal)', ' pyi_build_wheels pyi_upload_to_pypi pyi_commit pyi_github_release
echo 'have been defined. When you\'re ready, run each of those (in that order).'
