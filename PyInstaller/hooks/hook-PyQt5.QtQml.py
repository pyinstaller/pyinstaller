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
    """

    def __init__(self):
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
        self.pyqt_folder = ''
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
        self.analysis_file = a_right
        if os.path.exists(self.analysis_file):
            path_splits = os.path.split(self.analysis_file)
            # the folder the main py file is in
            self.analysis_folder = path_splits[0]
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
                        query = '.' + search_query + '[(].*?.*?.*?[)]'
                        hyp_file = re.findall(query, str(line))

                        if hyp_file:
                            # we will use the first file
                            first = hyp_file[0].replace(search_query, '')
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
        if os.path.exists(self.main_qml):
            return False
        else:
            self.append_to_data(self.analysis_folder, self.main_qml)
            self._first_handle(self.analysis_folder, self.main_qml)

    def _crawl_qml_file(self, c_file):

        # This is where we parse the qml file to look for
        # import statements.

        with open(c_file, mode='r', encoding='utf-8') as fh:
            for line in fh:
                if re.findall('[ ]+[//]', line):
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
            self._sanitize_imports(import_stats[0])

    def _sanitize_imports(self, stat):

        # Remove the (') apostrophies that comes
        # which are found in them
        if len(stat) > 8:
            clean = stat[7:-1]
            if clean not in self.raw_import_stats:
                self.raw_import_stats.append(clean)
        else:
            # Unkwown import type
            return False

    def find_images(self, statement):
        for keyword in self.image_search_words:
            img_query = re.findall('["|\'].*?.*?.*?[.]' + keyword + '["|\']',
                                   statement)
            if img_query:
                # since we are parsing the qml
                # line by line, there is only one entry
                # first_split = re.split(keyword+':\s?', img_query[0])
                self._sanitize_image_string(img_query[0])

    def _sanitize_image_string(self, statement):
        if statement[0] == '"':
            # maybe the user added a comment after the line
            # the splits will take it away into the third index
            splits = re.split('"', statement)
            url = splits[1]
        elif statement[0] == "'":
            # maybe the user added a comment after the line
            # the splits will take it away into the third index
            splits = re.split("'", statement)
            url = splits[1]
        else:
            # Unkwown type
            pass

        # find out if it is a relative url
        # and not a qrc
        if self.is_raw_img_str(url):
            # get the relative folder to the qml file
            # we are parsing
            splits = os.path.split(self.current_qml_file)
            current_folder = splits[0]
            # Get the path to the image we want to add
            full_path = os.path.join(current_folder, url)
            # convert to abs path since os.path.join
            abs_path = os.path.abspath(full_path)
            final_splits = os.path.split(abs_path)
            folder = final_splits[0]
            final_file = final_splits[1]
            # send it to be added to the datas file
            self.append_to_data(folder, final_file)
        else:
            return False

    def is_raw_img_str(self, string):
        # Here we find out if the string is
        # a relative string and not a full path or a varible
        # or a qrc
        if re.findall('qrc:', string):
            # It is a qrc
            return False
        else:
            # lets test if it is a relative path
            if os.path.exists(string):
                return False
            else:
                # it's a relative path
                return True

    def _first_handle(self, folder, file):

        # This is to first parse the
        # main qml file, that was first loaded seperately.

        full_path = os.path.join(folder, file)
        self._crawl_qml_file(full_path)
        splits = os.path.split(full_path)
        self._handle_imports(splits[0])

    def _handle(self, folder, file):

        # This is to organise the processs
        # to allow re-usability

        full_path = os.path.join(folder, file)
        self._crawl_qml_file(full_path)
        splits = os.path.split(full_path)
        self._handle_imports(splits[0])

    def _handle_imports(self, folder):

        # This is where we add the
        # js files if any,
        # and send off the genuine qt imports statements

        for each in self.raw_import_stats:

            entry = each.replace("'", '"')
            if len(re.findall('.js"', entry)) > 0:
                # js
                first = entry.split('"')
                js_file = first[1]
                self.raw_import_stats.remove(each)
                self.append_to_data(folder, js_file)

            elif entry[0] == '"':
                # it is an imported folder
                # just ignore it will be handled later
                continue

            else:
                # real Qt imports
                self.raw_import_stats.remove(each)
                self._sanitize_hidd_imps(each)

        # This seperation is to ensure we are done with a folder
        # before moving on to the next
        # Problems can emerge if the folders are nested.
        # This seperation prevents them

        for each in self.raw_import_stats:

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
        splits = raw_stat.split('.')
        stat = splits[0]

        if stat not in self.only_qml_imps_map:
            imp_stat = self.hidd_imps_map[stat]

            if imp_stat not in self.hidden_imports:
                self.hidden_imports.append(imp_stat)
        else:
            imp_stat = self.only_qml_imps_map[stat]
            self._imported_qml(imp_stat)

    def _imported_qml(self, module):

        # Here is where we import the needed
        # qml only imports
        # that has no python import statement

        relative_path = os.path.join('Qt', 'qml', module)
        qml_folder = os.path.join(self.pyqt_folder, relative_path)
        contents = qml_folder
        group = (contents, os.path.join('PyQt5', relative_path))
        self.datas.append(group)

    def _find_other_qml_files(self, folder):

        # Here we import all qml files
        # that are found in an imported
        # folder.
        # Not recursively though.
        # There could be a better way of doing this.

        contents = os.listdir(folder)
        for entry in contents:
            if entry[-4:] == '.qml':
                self.append_to_data(folder, entry)
                self._handle(folder, entry)
            else:
                continue

    def append_to_data(self, folder, file):

        # Here we just add files to be
        # imported to the datas variable
        # which will be added to the 'datas'
        # global variable

        full_path = os.path.join(folder, file)
        # this is to check for nesting
        # remove the starting folder,
        # whatever we have is the nested path
        neut_analys_folder = os.path.abspath(self.analysis_folder)
        neut_folder = os.path.abspath(folder)
        nest = neut_folder.replace(neut_analys_folder, '')
        # replace backslashes with forward slashes on windows
        # lets have a common ground to work with
        if nest != '':
            rem_folder = '.' + nest
        else:
            rem_folder = ''

        splits = os.path.split(file)

        if rem_folder != '':
            o_folder = rem_folder

        elif splits[0] == '':
            o_folder = '.'

        else:
            o_folder = splits[0]

        group = (full_path, o_folder)
        self.datas.append(group)

        # include also the qmlc
        # when available, since
        # since it speeds up the starting time.
        qmlc_path = full_path.replace('qml', 'qmlc')

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
        pyqt_folder = os.path.split(hook_api.__file__)[0]
        imports = QmlImports()
        imports.pyqt_folder = pyqt_folder
        if imports.start():
            h_imps, dts = imports.getValues()

            if h_imps != []:
                # send the hidden import statements
                # into the global variable
                for each in h_imps:
                    hook_api.add_imports(each)

            if dts != []:
                # send the QmlImports data variable
                # into the main stream datas variable.
                hook_api.add_datas(dts)
        else:
            return
