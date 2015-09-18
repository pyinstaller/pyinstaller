#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.lib.modulegraph.modulegraph import RuntimeModule
import PyInstaller.utils.hooks as hookutils

def hook(module_graph):
    """
    Add the `six.moves` module as a dynamically defined runtime module node and
    all modules mapped by `six._SixMetaPathImporter` as aliased module nodes to
    the passed graph.

    The `six.moves` module is dynamically defined at runtime by the `six` module
    and hence cannot be imported in the standard way. Instead, this hook adds a
    placeholder node for the `six.moves` module to the graph, which implicitly
    adds an edge from that node to the node for its parent `six` module. This
    ensures that the `six` module will be frozen into the executable. (Phew!)

    `six._SixMetaPathImporter` is a PEP 302-compliant module importer converting
    imports independent of the current Python version into imports specific to
    that version (e.g., under Python 3, from `from six.moves import tkinter_tix`
    to `import tkinter.tix`). For each such mapping, this hook adds a
    corresponding module alias to the graph allowing PyInstaller to translate
    the former to the latter.
    """
    # Dictionary from conventional module names to "six.moves" attribute names
    # (e.g., from `tkinter.tix` to `six.moves.tkinter_tix`).
    real_to_six_module_name = hookutils.eval_statement(
'''
import six
print('{')

# Iterate over the "six._moved_attributes" list rather than the
# "six._importer.known_modules" dictionary, as "urllib"-specific moved modules
# are overwritten in the latter with unhelpful "LazyModule" objects.
for moved_module in six._moved_attributes:
    # If this is a moved attribute rather than module, skip to the next object.
    if not isinstance(moved_module, six.MovedModule):
        continue
    print('  %s: %s,' % (
        repr(moved_module.mod), repr('six.moves.' + moved_module.name)))

print('}')
''')

    module_graph.add_module(RuntimeModule('six.moves'))
    for real_module_name, six_module_name in real_to_six_module_name.items():
        module_graph.alias_module(real_module_name, six_module_name)
