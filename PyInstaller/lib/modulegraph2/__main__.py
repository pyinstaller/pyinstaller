"""
Commandline interface

- Generate graph from one or more modules/scripts
- Export graph as:
    - HTML
    - dotfile
    - table
- Should be minimal wrapper around other functionality
  to make testing easier.
"""
from ._modulegraph import ModuleGraph
from ._dotbuilder import export_to_dot
import sys

mg = ModuleGraph()
mg.add_script("demo.py")

export_to_dot(sys.stdout, mg)
