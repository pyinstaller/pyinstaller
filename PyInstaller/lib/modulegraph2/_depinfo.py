import dataclasses
from typing import Optional

from ._importinfo import ImportInfo


@dataclasses.dataclass(frozen=True)
class DependencyInfo:
    """
    A frozen dataclass representing information about
    the dependency edge between two graph nodes.

    Attributes:
      is_optional
        True if the import appears to be optional

      is_global
        True if the import affects global names in the module

      in_fromlist
        True if the name is imported in the name list of
        an ``from ... import ...`` statement

      imported_as:
        Rename for this module (``import ... as impoted_as``),
        None when there is no ``as`` clause.
    """

    is_optional: bool
    is_global: bool
    in_fromlist: bool
    imported_as: Optional[str]


def from_importinfo(import_info: ImportInfo, in_fromlist: bool, name: Optional[str]):
    """
    Create an :class:`DependencyInfo` instance from an
    :class:`ImportInfo` and additional information.

    Args:
      import_info
        The :class:`ImportInfo` found by the AST or bytecode scanners

      in_fromlist
        True if the import refers to a name in the namelist
        from an ``from ... imoprt ...`` statement.

      name:
        Rename for the module (``import ... as name``), None
        when there was no ``as`` clause.
    """
    return DependencyInfo(
        import_info.is_optional, import_info.is_global, in_fromlist, name
    )
