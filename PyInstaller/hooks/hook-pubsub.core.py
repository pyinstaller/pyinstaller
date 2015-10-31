from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules('pubsub')

# collect_submodules does not find `arg1` or `kwargs` because
# they are not packages, just folders without an `__init__.py`
# Thus they are invisible to ModuleGraph and must be included as data files

pubsub_datas = collect_data_files('pubsub', include_py_files=True)


def _match(dst):
    return "kwargs" in dst or "arg1" in dst

datas = [(src, dst) for src, dst in pubsub_datas if _match(dst)]
