#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
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
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, \
    eval_statement

hiddenimports = (
    # Per http://sphinx-doc.org/extensions.html#builtin-sphinx-extensions,
    # Sphinx extensions are all placed in ``sphinx.ext``. Include these.
    collect_submodules('sphinx.ext') +
    #
    # The following analysis applies to Sphinx v. 1.3.1, reported by "pip show
    # sphinx".
    #
    # From sphinx.application line 429:
    #
    #    mod = __import__(extension, None, None, ['setup'])
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
    collect_submodules('sphinx.websupport.search') +
    collect_submodules('sphinx.domains') +
    #
    # From sphinx.cmdline line 173:
    #
    #    locale = __import__('locale')  # due to submodule of the same name
    #
    # Add this module.
    ['locale'] +
    #
    # Sphinx relies on a number of built-in extensions that are dynamically
    # imported. Collect all those.
    list(eval_statement("""
        from sphinx.application import builtin_extensions
        print(builtin_extensions)
    """))
)

# Sphinx also relies on a number of data files in its directory hierarchy: for
# example, *.html and *.conf files in ``sphinx.themes``, translation files in
# ``sphinx.locale``, etc.
datas = collect_data_files('sphinx') + collect_data_files('alabaster')
