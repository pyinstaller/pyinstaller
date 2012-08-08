from PyInstaller.hooks.hookutils import exec_statement

mpl_data_dir = exec_statement(
    "import matplotlib; print matplotlib._get_data_path()")

datas = [
    (mpl_data_dir, ""),
]
