# This is needed to bundle cacert.pem that comes with websocket module, similar to what is done with python "requests"

from PyInstaller.utils.hooks import collect_data_files
datas = collect_data_files('websocket')
