from PyInstaller.hooks.hookutils import exec_statement

hiddenimports = ["babel.dates"]

babel_localedata_dir = exec_statement(
    "import babel.localedata; print babel.localedata._dirname")

datas = [
    (babel_localedata_dir, ""),
]
