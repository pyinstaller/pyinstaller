import dataclasses
from typing import Optional


@dataclasses.dataclass(frozen=True)
class DependencyInfo:
    optional: bool
    fromlist: bool


def merged_depinfo(
    first: Optional[DependencyInfo], second: Optional[DependencyInfo]
) -> Optional[DependencyInfo]:
    if first is None:
        if second is None:
            return None

        return DependencyInfo(False, second.fromlist)
    elif second is None:
        return DependencyInfo(False, first.fromlist)

    conditional = first.optional and second.optional
    fromlist = first.fromlist and second.fromlist

    return DependencyInfo(conditional, fromlist)
