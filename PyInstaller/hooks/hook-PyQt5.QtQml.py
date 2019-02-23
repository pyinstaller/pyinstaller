#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
import os
import sys
import re
import glob

from PyInstaller.utils import misc
from PyInstaller.utils.hooks import pyqt5_library_info, add_qt5_dependencies
from PyInstaller import log as logging

logger = logging.getLogger(__name__)

hiddenimports, binaries, datas = add_qt5_dependencies(__file__)

qmldir = pyqt5_library_info.location['Qml2ImportsPath']
# Per https://github.com/pyinstaller/pyinstaller/pull/3229#issuecomment-359735031,
# not all PyQt5 installs have QML files. In this case, ``qmldir`` is empty. In
# addition, the directory may not exist even if ``qmldir`` is not empty, per
# https://github.com/pyinstaller/pyinstaller/issues/3864.
if not os.path.exists(qmldir):
    logger.warning('Unable to find Qt5 QML files. QML files not packaged.')
else:
    qml_rel_dir = ['PyQt5', 'Qt', 'qml']
    datas += [(qmldir, os.path.join(*qml_rel_dir))]
    binaries += [
        # Produce ``/path/to/Qt/Qml/path_to_qml_binary/qml_binary,
        # PyQt5/Qt/Qml/path_to_qml_binary``. When Python 3.4 goes EOL (see
        # PEP 448), this is better written as
        # ``os.path.join(*qml_rel_dir,
        # os.path.dirname(os.path.relpath(f, qmldir))))``.
        (f, os.path.join(*(qml_rel_dir +
                           [os.path.dirname(os.path.relpath(f, qmldir))])))
        for f in misc.dlls_in_subdirs(qmldir)
    ]


class QmlImports():

    """
    Finds all Qml files used in the main project and parses those qml files
    to include all imports including Javascript files and folders.

    It finds the initial qml file by:
        1. Reading the (.spec) file to find the main python file
        2. Reading the main python file which is by now called the analysis
        file, to find the qml files imported, using the
        self.read_analysis_file().
        3. The self.read_analysis_file() uses two search queries(load,
        setSource) which are the only two used by QmlApplicationEngine class to
        load qml files.
        4. The call to self.is_raw_string() checks to see if the contents of 
        the load() or setSource() is not a variable or even a qrc.

    """

    def __init__(self, folder):
        self.hidden_imports = []
        self.datas = []
        self.raw_import_stats = []
        self.analysis_file = ''
        self.analysis_folder = ''
        self.main_qml = ''
        self.current_qml_file = ''
        self.recently_added_paths = set(sys.path[-2:])
        self.spec_files = []
        self.spec_file = ''
        self.search_words = ['load', 'setSource']
        self.image_search_words = ['png', 'jpeg', 'jpg', 'tiff', 'gif', 'ico']
        self.only_qml_imps_map = {"QtGraphicalEffects 1": "QtGraphicalEffects",
                                  "QtCanvas3D 1": "QtCanvas3D",
                                  "Qt": "Qt"}
        self.hidd_imps_map = {'QtQuick 2': 'PyQt5.QtQuick',
                              'QtQuick': 'PyQt5.QtQuick',
                              'QtPositioning 5': 'PyQt5.QtPositioning',
                              'QtWebEngine 1': "PyQt5.QtWebEngine",
                              'QtPurchasing 1': "PyQt5.QtPurchasing",
                              'QtMultimedia 5': "PyQt5.QtMultimedia",
                              'QtSensors 5': 'PyQt5.QtSensors',
                              'QtWinExtras 1': 'PyQt5.QtWinExtras',
                              'QtLocation 5': 'PyQt5.QtLocation',
                              'QtNfc 5': 'PyQt5.QtNfc',
                              'QtScxml 5': 'PyQt5.QtScxml',
                              'QtWebSockets 1': 'PyQt5.QtWebSockets',
                              'QtWebChannel 1': 'PyQt5.QtWebChannel',
                              'QtGamepad 1': 'PyQt5.QtGamepad',
                              'QtCharts 2': 'PyQt5.QtCharts',
                              'QtWebView 1': 'PyQt5.QtWebView'}
        self.pyqt_folder = folder
        self.nest = 0

    def start(self):

        # This function is to ensure that
        # certain variables are first set
        # before the processes begin
        self.find_spec()
        if self.spec_file != '':
            if self.find_analysis_file():
                if not self.read_analys_file():
                    return False
                else:
                    self.reconstruct_qml_path()
                    return True
            else:
                return False

    def find_spec(self):

        # The is the function that look for the spec file
        # We need to this to find the (.py) file that PyInstaller
        # is analysing
        for file_path in self.recently_added_paths:
            files = os.listdir(file_path)

            # search the files
            for entry in files:

                if entry.endswith('.spec'):

                    self.spec_files.append(os.path.join(file_path, entry))

                else:
                    continue

        if len(self.spec_files) > 1:
            self.spec_file = self.clarify_specs()
        else:
            self.spec_file = self.spec_files[0]

    def clarify_specs(self):

        # if there are two specs
        # here we clarify them
        # to see which one is the most current
        t_s = []
        file_info = dict()
        for path in self.spec_files:
            stats = os.stat(path)
            file_info[int(stats.st_mtime)] = path
            t_s.append(int(stats.st_mtime))

        # set the most seconds to the highest variable
        highest = 0
        for entry in t_s:
            if entry > highest:
                highest = entry
            else:
                continue
        # the file info dict actually returns the path
        # whose key has been verified as the most seconds
        return file_info[highest]

    def find_analysis_file(self):

        # This is where we find the py file
        # that PyInstaller is first reading by
        # analysing the spec file

        # Read spec file
        with open(self.spec_file, mode='rb') as spec:

            data = spec.read()

        # find the line that contains the analysis variable
        analysis = re.findall('a = .*?.*?.*?,', str(data))

        # strip extraneous data
        without_com = analysis[0].replace(',', '')
        without_analy_stat = without_com.replace('a = Analysis(', '')
        without_apos = without_analy_stat.replace("'", "")
        a_right = without_apos[1:-1]

        # the main python file
        if not os.path.isabs(a_right):
            self.analysis_file = os.path.join(os.path.dirname(self.spec_file),
                                              a_right)
        else:
            self.analysis_file = a_right

        if os.path.exists(self.analysis_file):
            self.analysis_folder = os.path.dirname(self.analysis_file)
            return True
        else:
            return False

    def read_analys_file(self):

        # This is where we read the main python file
        # to find the main qml file used.

        with open(self.analysis_file, mode='rb') as analys:
            for line in analys:
                if re.findall('[ ]+[#]', str(line)):
                    # skip it is a comment in the code
                    continue
                else:
                    # find line that contains a qml file
                    for search_query in self.search_words:
                        # query should end up looking like: .load("anyQmlFile")
                        query = '.' + search_query + '[(].*?.*?.*?[)]'
                        hyp_file = re.findall(query, str(line))

                        if hyp_file:
                            # QmlEngine takes only one qml file
                            # if comments are taken out then it's probably the,
                            # only one, so the hyp_file is a list that contains
                            # just one entry.
                            first = hyp_file[0].replace(search_query, '')
                            # remove the dot(.) and the opening and closing
                            # brackets
                            second = first[2:-1]
                            if self.is_raw_string(second):
                                return True
                            else:
                                return False
                            break

                        else:
                            continue

    def is_raw_string(self, raw):

        # Here we read the line to see if there is
        # a genuine qml filepath.
        if re.findall('([+]|,|[)])', raw) or not re.findall('(\'|")', raw):
            # It is a variable
            return False

        else:
            if re.findall('qrc:', raw):  # it is a qrc
                return False
            else:
                if raw[0] == '"':
                    self.main_qml = raw.replace('"', '')
                    return True

                elif raw[0] == "'":
                    self.main_qml = raw.replace("'", "")
                    return True
                else:
                    return False

    def reconstruct_qml_path(self):

        # This is where we verify if the
        # qml filepath is a relative path
        # to the application's folder
        # if it's not, we simply do nothing.
        # it can't be a full path.
        if not os.path.isabs(self.main_qml):
            self.append_to_data(self.analysis_folder, self.main_qml)
            self._start_process(self.analysis_folder, self.main_qml) # start

    def _crawl_qml_file(self, c_file):

        # This is where we parse the qml file to look for
        # import statements.

        with open(c_file, mode='r', encoding='utf-8') as fh:
            for line in fh:
                if re.match(r'\s*//', line):
                    # skip it's a comment line
                    continue
                else:
                    self.find_imports(line)
                    # set the qml file to the current qml file
                    # since the image path should be relative to
                    # that file
                    self.current_qml_file = c_file
                    self.find_images(line)

    def find_imports(self, statement):
        import_stats = re.findall('import .*?.*?.*?$', statement)
        if import_stats:
            # since we are parsing this line by line
            # there will always be just one entry in import stats

            if '"' in import_stats[0] or "'" in import_stats[0]:
                # Remove the (') apostrophies that comes
                # which are found in them
                if len(import_stats[0]) > 8:
                    stat = import_stats[0][7:-1]
            else:
                stat = import_stats[0]

            if stat not in self.raw_import_stats:
                self.raw_import_stats.append(stat)

    def find_images(self, statement):
        for keyword in self.image_search_words:
            stat = statement.replace("'", '"')
            if '.' + keyword in stat:
                img_query = stat.split('"', 2)[1]
    
                if img_query:
                    self._sanitize_image_string(img_query)

    def _sanitize_image_string(self, url):
        # find out if it is a relative url
        # and not a qrc
        if not url.startswith("qrc:") and not os.path.isabs(url):
            # get the relative folder to the qml file
            # we are parsing
            splits = os.path.split(self.current_qml_file)
            current_folder = splits[0]
            # Get the path to the image we want to add
            full_path = os.path.join(current_folder, url)
            # convert to abs path since os.path.join
            folder, final_file = os.path.split(os.path.abspath(full_path))
            # send it to be added to the datas file
            self.append_to_data(folder, final_file)
        else:
            return False

    def _start_process(self, folder, file):

        # This is to organise the processs
        # to allow re-usability

        full_path = os.path.join(folder, file)
        self._crawl_qml_file(full_path)
        self._handle_imports(os.path.dirname(full_path))

    def _handle_imports(self, folder):

        # This is where we add the
        # js files if any,
        # and send off the genuine qt imports statements

        for each in self.raw_import_stats:

            # each may contiain "'myFunction.js'"
            entry = each.replace("'", '"')
            if '.js' in entry:
                # js
                js_file = entry.split('"', 2)[1]
                self.raw_import_stats.remove(each)
                self.append_to_data(folder, js_file)

            elif entry[0] == '"':
                # This will oly match if it is an imported folder
                # just ignore, it will be handled later
                continue

            else:
                # real Qt imports
                self.raw_import_stats.remove(each)
                self._sanitize_hidd_imps(each)

        for each in self.raw_import_stats:
            # This seperation is to ensure we are done with a folder
            # before moving on to the next
            # Problems can emerge if the folders are nested.
            # This seperation prevents them

            entry = each.replace("'", '"')
            if entry[0] == '"':
                # folder
                full_path = os.path.join(folder, entry.replace('"', ''))
                self.raw_import_stats.remove(each)
                self._find_other_qml_files(full_path)

    def _sanitize_hidd_imps(self, raw_stat):

        # Statements in qml and it's corresponding statements
        # in python obviously differ
        # here is where we find the corresponding pyton statements

        # split the nos out and lets handle the real import
        stat = raw_stat.split('.', 1)[0]

        if stat not in self.only_qml_imps_map:
            if stat in self.hidd_imps_map:
                imp_stat = self.hidd_imps_map[stat]
                self.hidden_imports.append(imp_stat)
        else:
            # Here is where we import the needed
            # qml only imports
            # that has no python import statement
            # regex is used to find module, so custom frameworks can be found
            module = re.split('\s\d$', stat)[0]
            relative_path = os.path.join('Qt', 'qml', module)
            qml_folder = os.path.join(self.pyqt_folder, relative_path)
            group = (qml_folder, os.path.join('PyQt5', relative_path))
            self.datas.append(group)

    def _find_other_qml_files(self, folder):

        # Here we import all qml files
        # that are found in an imported
        # folder.
        # Not recursively though.
        # There could be a better way of doing this.

        for entry in glob.glob(os.path.join(folder, '*.qml')):
            self.append_to_data(folder, entry)
            self._start_process(folder, entry)

    def append_to_data(self, folder, file):

        # Here we just add files to be
        # imported to the datas variable
        # which will be added to the 'datas'
        # global variable

        full_path = os.path.join(folder, file)
        # this is to check for nesting
        # remove the starting folder,
        # whatever we have is the nested path
        nest = os.path.relpath(os.path.abspath(folder),
                               os.path.abspath(self.analysis_folder))

        if nest != '.':
            rem_folder = nest
        else:
            # there is no trailing folder
            rem_folder = ''

        # file may contain "images/icon.ico"
        splits = os.path.split(file)

        # There is a trialing folder, set it as output folder
        if rem_folder != '':
            o_folder = rem_folder

        elif splits[0] == '':
            o_folder = '.'

        else:
            # splits[0] may sometime contain "images"
            o_folder = splits[0]

        group = (full_path, o_folder)
        self.datas.append(group)

        # include also the qmlc
        # when available, since it speeds up the starting time.
        qmlc_path = full_path.replace('.qml', '.qmlc')

        if os.path.exists(qmlc_path):
            splits = os.path.split(file)
            qmlc_group = (qmlc_path, o_folder)
            self.datas.append(qmlc_group)

    def getValues(self):

        # Here we return the variable
        # datas and hidden_imports
        # This function will be called
        # seperately for the values
        # They will then go into the global variables store

        # Return the values
        return self.hidden_imports, self.datas


def hook(hook_api):

        # Find the folder in which PyQt in located
        pyqt_folder = os.path.dirname(hook_api.__file__)
        imports = QmlImports(pyqt_folder)
        if imports.start():
            h_imps, dts = imports.getValues()
            # send the hidden import statements
            # into the global variable
            for imp in h_imps:
                hook_api.add_imports(imp)

            # send the QmlImports data variable
            # into the main stream datas variable.
            hook_api.add_datas(dts)
