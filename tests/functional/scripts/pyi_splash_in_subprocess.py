import sys
import subprocess
import time

in_child = False
if len(sys.argv) == 2:
    assert sys.argv[1] == 'child', f"Unexpected argument: {sys.argv[1]}"
    in_child = True

# pyi_splash must be should be always importable
import pyi_splash  # noqa: E402

# Check module's guts to validate its state. Not for public use...

# Module must be marked as initialized, regardless of whether splash screen is active or suppressed.
assert pyi_splash._initialized, "Module is not marked as initialized!"

if in_child:
    # IPC port must be zero
    assert pyi_splash._ipc_port == 0, f"Unexpected IPC port value: {pyi_splash._ipc_port}"

    # Connection must be left closed
    assert pyi_splash._ipc_socket_closed, \
        "Unexpected splash screen socket state - expected it to be closed, but it is open!"
else:
    # IPC port must be valid
    assert pyi_splash._ipc_port > 0, f"Unexpected IPC port value: {pyi_splash._ipc_port}"

    # Connection must have been established
    assert not pyi_splash._ipc_socket_closed, \
        "Unexpected splash screen socket state - expected it to be open, but it is closed!"

# Test of public API

# is_alive() should reflect the actual status (True in parent, False in child process).
assert pyi_splash.is_alive() != in_child, "Unexpected splash screen status!"

# update_text() should either succeed or be a no-op. Most importantly, it should not raise an error when splash
# screen is suppressed.
pyi_splash.update_text("Updated text")
time.sleep(1)

# Same goes for close().
pyi_splash.close()

# After close, splash screen should be inactive (if it ever was active)
assert not pyi_splash.is_alive(), "Splash screen is not inactive!"

# If we are the parent process, spawn the child
if not in_child:
    print("Spawning the child process...", file=sys.stderr)
    subprocess.run([sys.executable, "child"], check=True)
