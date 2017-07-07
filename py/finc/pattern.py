from typing import List
from . import builtin
from . import types
from . import symbols


class Pattern:
    TESTED: bool
    type: types.Type

    def bound(self) -> bool:
        raise NotImplementedError()

    def variables(self) -> List['Variable']:
        return []

    def resolve(self, res: types.Resolution) -> None:
        self.type = self.type.resolve(res)

    def finalize(self) -> bool:
        return self.type.finalize()


class Any(Pattern):
    TESTED = False

    def __init__(self) -> None:
        self.type = builtin.VOID

    def __str__(self) -> str:
        return '_'

    def bound(self) -> bool:
        return False


class Int(Pattern):
    TESTED = True

    def __init__(self, value: int) -> None:
        self.value = value
        self.type = builtin.INT

    def __str__(self) -> str:
        return str(self.value)

    def bound(self) -> bool:
        return False


class Float(Pattern):
    TESTED = True

    def __init__(self, value: float) -> None:
        self.value = value
        self.type = builtin.FLOAT

    def __str__(self) -> str:
        return str(self.value)

    def bound(self) -> bool:
        return False


class Variable(Pattern):
    TESTED = False

    def __init__(self, name: str, tp: types.Type) -> None:
        self.name = name
        self.type = tp

    def __str__(self) -> str:
        return f'{self.name} {self.type}'

    def bound(self) -> bool:
        return True

    def variables(self) -> List['Variable']:
        return [self]


class Struct(Pattern):
    def __init__(self, struct: symbols.Struct) -> None:
        self.struct = struct
        self.type = types.StructType(struct)

    def bound(self) -> bool:
        return False


class Variant(Pattern):
    TESTED = True

    def __init__(self, variant: symbols.Variant) -> None:
        self.variant = variant
        self.type = types.EnumerationType(variant.enum)

        self.field_patterns: List[Pattern] = []
        self.fields: types.Variables = None

    def __str__(self) -> str:
        res = str(self.variant)
        if len(self.field_patterns) > 0:
            res += '(' + ', '.join(str(f) for f in self.field_patterns) + ')'

        return res

    def bound(self) -> bool:
        return any(f.bound() for f in self.field_patterns)

    def variables(self) -> List[Variable]:
        vs = []
        for pat in self.field_patterns:
            vs.extend(pat.variables())

        return vs

    def resolve(self, res: types.Resolution) -> None:
        super().resolve(res)

        # get the actual fields of the variant
        assert isinstance(self.type, types.EnumerationType)
        self.fields = self.type.variants[self.variant.value].resolve(res)

    def finalize(self) -> bool:
        return super().finalize() and self.fields.finalize()

    def add_field(self, pat: Pattern) -> None:
        self.field_patterns.append(pat)
