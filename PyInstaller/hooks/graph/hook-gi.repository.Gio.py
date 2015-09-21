from PyInstaller.lib.modulegraph.modulegraph import RuntimeModule


def hook(module_graph):
    module_graph.add_module(RuntimeModule('gi.repository.Gio'))
