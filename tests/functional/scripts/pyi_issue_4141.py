import os
import sys
from pathlib import Path

# Import the application's "app" package. This does not(!) contain a sub-module app.hook.
import app  # noqa: F401

# Paths from #4141, where the script was called "main"
#   dist/main/app.py
#   p/plugin_1/app.py
# Paths here:
#   dist/pyi_issue_4141/app.py
#   my-plugins/plugin_11/app.py
dist_main_len = len(os.path.join("dist", "main"))

# Create some "plugins" in sub-directory "p".
#
# Each plugin contains a sub-module called app.hook, which gets imported by the plugin's main module.
# If PyInstaller picks up the application's "app" package instead of the plugin's (which is issue #4141),
# importing the app.hook sub-module will fail.
plugins_dir = Path("p").absolute()
plugin_names = [chr(ord("a") + 10 + i) * (dist_main_len + i) for i in range(5, -5, -1)]
print(plugin_names)

for pn in plugin_names:
    print(plugins_dir / pn / "app")
    (plugins_dir / pn / "app").mkdir(parents=True, exist_ok=True)
    (plugins_dir / pn / "__init__.py").write_text("from .app import hook")
    (plugins_dir / pn / "app" / "hook.py").touch()
del pn

sys.path.insert(0, str(plugins_dir))
print("sys.path[0]:", sys.path[0])

for plugin in plugin_names:
    mod = __import__(plugin)
    print(mod)
    # double check
    assert mod.__file__ == str(plugins_dir / plugin / "__init__.py")
