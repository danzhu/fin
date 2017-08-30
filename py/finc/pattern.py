from typing import List, Union, Any, Iterator
from itertools import chain
from . import builtin
from . import types
from . import symbols


class Pattern:
    type: types.Type

    def tested(self) -> bool:
        raise NotImplementedError()

    def bound(self) -> bool:
        raise NotImplementedError()

    def variables(self) -> Iterator['Variable']:
        return iter([])

    def resolve(self, res: types.Resolution) -> None:
        self.type = self.type.resolve(res)


class Wildcard(Pattern):
    def __init__(self) -> None:
        self.type = builtin.VOID

    def __str__(self) -> str:
        return '_'

    def tested(self) -> bool:
        return False

    def bound(self) -> bool:
        return False


class Constant(Pattern):
    def __init__(self, value: Any, tp: types.Type) -> None:
        self.value = value
        self.type = tp

    def __str__(self) -> str:
        return str(self.value)

    def tested(self) -> bool:
        return True

    def bound(self) -> bool:
        return False


class Variable(Pattern):
    def __init__(self, name: str, tp: types.Type) -> None:
        self.name = name
        self.type = tp

        self.variable: symbols.Variable = None

    def __str__(self) -> str:
        return f'{self.name} {self.type}'

    def tested(self) -> bool:
        return False

    def bound(self) -> bool:
        return True

    def variables(self) -> Iterator['Variable']:
        return iter([self])

    def set_variable(self, var: symbols.Variable) -> None:
        self.variable = var


class Struct(Pattern):
    def __init__(self, src: Union[symbols.Struct, symbols.Variant]) -> None:
        self.source = src

        if isinstance(src, symbols.Struct):
            self.type = types.StructType(src)
        elif isinstance(src, symbols.Variant):
            self.type = types.EnumerationType(src.enum)
        else:
            assert False

        self.subpatterns: List[Pattern] = []
        self.fields: types.Variables = None

    def __str__(self) -> str:
        res = str(self.source)
        if len(self.subpatterns) > 0:
            res += '(' + ', '.join(str(f) for f in self.subpatterns) + ')'

        return res

    def tested(self) -> bool:
        # variants are always tested
        if isinstance(self.source, symbols.Variant):
            return True

        # otherwise, depends on fields
        return any(p.tested() for p in self.subpatterns)

    def bound(self) -> bool:
        return any(p.bound() for p in self.subpatterns)

    def variables(self) -> Iterator[Variable]:
        return chain.from_iterable(pat.variables() for pat in self.subpatterns)

    def resolve(self, res: types.Resolution) -> None:
        super().resolve(res)

        # get the actual fields and resolve them
        if isinstance(self.type, types.StructType):
            self.fields = self.type.fields.resolve(res)
        elif isinstance(self.type, types.EnumerationType):
            assert isinstance(self.source, symbols.Variant)

            self.fields = self.type.variants[self.source.value].resolve(res)
        else:
            assert False

    def add_field(self, pat: Pattern) -> None:
        self.subpatterns.append(pat)
