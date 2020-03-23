Set-Location bootloader
# assume python in path, otherwise, need to enter venv first
python .\waf all
python .\waf all --target-arch=32bit
Set-Location ..