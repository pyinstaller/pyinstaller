import usb.core

# Detect usb devices.
devices = usb.core.find(find_all = True)

if not devices:
    raise SystemExit('No USB device found.')
