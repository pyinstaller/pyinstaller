from typing import Optional

import dataclasses

from ._importinfo import ImportInfo


@dataclasses.dataclass(frozen=True)
class DependencyInfo:
    is_optional: bool
    is_global: bool
    in_fromlist: bool
    imported_as: Optional[str]


def from_importinfo(import_info: ImportInfo, in_fromlist: bool, name: Optional[str]):
    return DependencyInfo(
        import_info.is_optional, import_info.is_global, in_fromlist, name
    )
