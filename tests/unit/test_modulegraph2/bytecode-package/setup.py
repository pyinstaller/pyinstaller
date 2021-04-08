from setuptools import setup
import os
import shutil
import py_compile

if os.path.exists("package"):
    shutil.rmtree("package")

# XXX: simple-package contains a package and
# a toplevel module. This variant only contains
# a package because wheel won't package modules
# that are only available as a bytecode file.
os.mkdir("package")
for nm in ["package/__init__.py", "package/module.py"]:

    src = os.path.join("src", nm)
    dst = nm + "c"

    py_compile.compile(src, dst, doraise=True)

setup(
    name="bytecode-package",
    version="1.0",
    description="This is a demo package",
    include_package_data=True,
    packages=["package"],
)
