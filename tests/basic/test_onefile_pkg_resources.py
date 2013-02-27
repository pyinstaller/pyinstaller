# With module 'pkg_resources' it should not matter if a file is stored
# on file system, in zip archive or bundled with frozen app.


import pkg_resources as res
import pkg3


# With frozen app the resources is available in directory
# os.path.join(sys._MEIPASS, 'pkg3/pkg_resources-data.txt')
data = res.resource_string(pkg3.__name__, 'pkg_resources-data.txt')
data = data.strip()


if not data == 'This is data text for testing freezing pkg_resources module.':
    raise SystemExit('Could not read data with pkg_resources module.')
