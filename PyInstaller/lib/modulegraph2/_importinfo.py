import dataclasses
from typing import Iterable, Optional, Set, Tuple


class import_name(str):
    """
    Value representing an imported name. The string
    value itself is the imported name, the *asname*
    attribute contains a rename from an "as" clause.

    Attributes:
       asname: Renamed name from an "as" clause
    """

    __slots__ = ["asname"]

    asname: Optional[str]

    @classmethod
    def from_tuple(cls, name_tuple: Tuple[str, Optional[str]]):
        result = cls(name_tuple[0])
        result.asname = name_tuple[1]
        return result


@dataclasses.dataclass(frozen=True)
class ImportInfo:
    """
    Information about an import statement found in the AST for a module or script

    Attributes:
      import_module
        The name of the module begin imported:
        ``import import_module`` or ``from module_name import ...``.

      import_level
        Number of dots at the start of an imported name,
        ``0`` for global imports, 1 or higher for relative
        imports.

      import_names
        The set of names imported with ``from import_module import ...``.

      star_import
        True if this describes ``from import_module import *``.

      is_in_function
        True if this describes an import statement in a function definition

      is_in_conditional
        True if this describes an import statement in a either branch
        of a conditional statement.

      is_in_tryexcept
        True if this describes an import statement in the ``try`` or
        ``except`` blocks of a try statement.
    """

    import_module: import_name
    import_level: int
    import_names: Set[import_name]
    star_import: bool
    is_in_function: bool
    is_in_conditional: bool
    is_in_tryexcept: bool

    @property
    def is_optional(self):
        """
        True if this describes an import statement that might be
        optional.
        """
        return self.is_in_function or self.is_in_conditional or self.is_in_tryexcept

    @property
    def is_global(self):
        """
        True if this describes an import statement at module level
        (and hence affects the set of globals in the module).
        """
        return not self.is_in_function


def create_importinfo(
    name: Tuple[str, Optional[str]],
    fromlist: Optional[Iterable[Tuple[str, Optional[str]]]],
    level: int,
    in_def: bool,
    in_if: bool,
    in_tryexcept: bool,
):
    """
    Create an :class:`ImportInfo` instance.

    Args:
      name: imported name
      fromlist: The "from" list of an import statement (or None)
      level: The import level, 0 for global imports and a positive
        number for relative imoprts.
      in_def: Import statement inside a function definition
      in_if: Import statement inside either branch of an if-statement
      in_tryexcept: Import statement in the try or except blocks of
        a try statement.

    Returns:
      A newly created :class:`ImportInfo` instance.
    """
    import_names: Set[import_name]

    have_star = False
    if fromlist is None:
        import_names = set()
    else:
        import_names = {import_name.from_tuple(item) for item in fromlist}
        if "*" in import_names:
            import_names.remove(import_name("*"))
            have_star = True

    return ImportInfo(
        import_module=import_name.from_tuple(name),
        import_level=level,
        import_names=import_names,
        star_import=have_star,
        is_in_function=in_def,
        is_in_conditional=in_if,
        is_in_tryexcept=in_tryexcept,
    )
