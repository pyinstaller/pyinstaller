#!/usr/bin/env fish


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
