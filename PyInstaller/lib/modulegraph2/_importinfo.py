from typing import Iterable, Optional, Set

import dataclasses


@dataclasses.dataclass(frozen=True)
class ImportInfo:
    """
    Information about an import statement found in the AST for a module or script
    """

    import_module: str
    import_level: int
    import_names: Set[str]
    star_import: bool
    is_in_function: bool
    is_in_conditional: bool
    is_in_tryexcept: bool

    @property
    def is_optional(self):
        return self.is_in_function or self.is_in_conditional or self.is_in_tryexcept

    @property
    def is_global(self):
        return not self.is_in_function


def create_importinfo(
    name: str,
    fromlist: Optional[Iterable[str]],
    level: int,
    in_def: bool,
    in_if: bool,
    in_tryexcept: bool,
):
    import_names: Set[str]

    have_star = False
    if fromlist is None:
        import_names = set()
    else:
        import_names = set(fromlist)
        if "*" in import_names:
            import_names.remove("*")
            have_star = True

    return ImportInfo(
        import_module=name,
        import_level=level,
        import_names=import_names,
        star_import=have_star,
        is_in_function=in_def,
        is_in_conditional=in_if,
        is_in_tryexcept=in_tryexcept,
    )
