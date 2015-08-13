from PyInstaller.compat import is_darwin
from PyInstaller.utils.hooks.hookutils import exec_statement

if is_darwin:  # TODO check if this is needed on linux
    datas = []
    files = exec_statement("""
import ssl
print(ssl.get_default_verify_paths().cafile)""").strip().split()
    for file in files:
        datas.append((file, 'lib'))  # TODO find a way to make sure the bundled cafile is always named 'cert.pem'
