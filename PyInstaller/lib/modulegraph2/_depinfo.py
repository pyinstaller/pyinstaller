import dataclasses


@dataclasses.dataclass(frozen=True)
class DependencyInfo:
    conditional: bool
    function: bool
    trueexcept: bool
    fromlist: bool
