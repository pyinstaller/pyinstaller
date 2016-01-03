#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
# ********************************************
# hook-sphinx.py - Pyinstaller hook for Sphinx
# ********************************************
from PyInstaller.utils.hooks import \
    collect_submodules, collect_data_files, is_module_satisfies

hiddenimports = (
# The following analysis applies to Sphinx v. 1.3.1, reported by "pip show
# sphinx".
#
# From sphinx.application line 248:
#
#    __import__('sphinx.builders.' + mod, None, None, [cls]), cls)
#
# Therefore, we need all modules in "sphinx.builders". Note this includes the
# "sphinx.builders.changes" module, which imports from the "sphinx.themes"
# module via import() rather than __import__(), which unconditionally imports
# the external "alabaster" and "sphinx_rtd_theme" modules again via import()
# rather than __import__(). While the data files for these themes must be listed
# below, these themes need *NOT* be listed as hidden imports here.
                  collect_submodules('sphinx.builders') +
#
# From sphinx.application line 429:
#
#    mod = __import__(extension, None, None, ['setup'])
#
# Per http://sphinx-doc.org/extensions.html#builtin-sphinx-extensions,
# Sphinx extensions are all placed in "sphinx.ext". Include these.
                  collect_submodules('sphinx.ext') +
#
# From sphinx.search line 228:
#
#    lang_class = getattr(__import__(module, None, None, [classname]),
#                         classname)
#
# From sphinx.search line 119:
#
#    languages = {
#        'da': 'sphinx.search.da.SearchDanish',
#        'de': 'sphinx.search.de.SearchGerman',
#        'en': SearchEnglish,
#
# So, we need all the languages in "sphinx.search".
                  collect_submodules('sphinx.search') +
#
# From sphinx.websupport line 100:
#
#    mod = 'sphinx.websupport.search.' + mod
#    SearchClass = getattr(__import__(mod, None, None, [cls]), cls)
#
# So, include modules under "sphinx.websupport.search".
                  collect_submodules('sphinx.websupport.search') +
#
# From sphinx.util.inspect line 21:
#
#    inspect = __import__('inspect')
#
# And from sphinx.cmdline line 173:
#
#    locale = __import__('locale')  # due to submodule of the same name
#
# Add these two modules.
                  ['inspect', 'locale'] )

# Sphinx also relies on a number of data files in its directory hierarchy: for
# example, *.html and *.conf files in sphinx.themes, translation files in
# sphinx.locale, etc.
datas = collect_data_files('sphinx')

# Sphinx 1.3.1 adds additional mandatory dependencies unconditionally imported
# by the "sphinx.themes" module regardless of the current Sphinx configuration:
# the "alabaster" and "sphinx_rtd_theme" themes, each relying on data files.
if is_module_satisfies('sphinx >= 1.3.1'):
    datas.extend(collect_data_files('alabaster'))
    datas.extend(collect_data_files('sphinx_rtd_theme'))
