from typing import List, Dict
from . import reflect
from . import symbols


class Pattern:
    TESTED: bool
    BOUND: bool
    type: reflect.Type

    def resolve(self, gens: Dict[str, reflect.Type]) -> None:
        self.type = self.type.resolve(gens)

    def variables(self) -> List['Variable']:
        return []


class Any(Pattern):
    TESTED = False
    BOUND = False

    def __init__(self) -> None:
        self.type = symbols.VOID

    def __str__(self) -> str:
        return '_'


class Int(Pattern):
    TESTED = True
    BOUND = False

    def __init__(self, value: int) -> None:
        self.value = value
        self.type = reflect.StructType(symbols.INT)

    def __str__(self) -> str:
        return str(self.value)


class Float(Pattern):
    TESTED = True
    BOUND = False

    def __init__(self, value: float) -> None:
        self.value = value
        self.type = reflect.StructType(symbols.FLOAT)

    def __str__(self) -> str:
        return str(self.value)


class Variable(Pattern):
    TESTED = False
    BOUND = True

    def __init__(self, name: str, tp: reflect.Type) -> None:
        self.name = name
        self.type = tp

    def __str__(self) -> str:
        return f'{self.name} {self.type}'

    def variables(self) -> List['Variable']:
        return [self]


# class Struct(Pattern):
#     def __init__(self, struct: reflect.Struct) -> None:
#         self.struct = struct


class Variant(Pattern):
    TESTED = True
    BOUND = True

    def __init__(self, variant: reflect.Variant) -> None:
        self.variant = variant
        self.type = reflect.EnumerationType(variant.enum)

        self.fields: List[Pattern] = []
        self.variant_struct: reflect.StructType = None

    def __str__(self) -> str:
        res = str(self.variant)
        if len(self.fields) > 0:
            res += '(' + ', '.join(str(f) for f in self.fields) + ')'

        return res

    def resolve(self, gens: Dict[str, reflect.Type]) -> None:
        super().resolve(gens)

        assert isinstance(self.type, reflect.EnumerationType)
        self.variant_struct = self.type.variants[self.variant.value]

    def variables(self) -> List[Variable]:
        vs = []
        for pat in self.fields:
            vs.extend(pat.variables())

        return vs

    def add_field(self, pat: Pattern) -> None:
        self.fields.append(pat)
