Remove-Item PyInstaller/bootloader/Windows-32bit/*.exe
Remove-Item PyInstaller/bootloader/Windows-64bit/*.exe

Set-Location bootloader
# assume python in path, otherwise, need to enter venv first
python .\waf all
python .\waf all --target-arch=32bit
Set-Location ..
