from typing import Any, Sequence, List, Dict, Iterator, Iterable, Union, Set
import math
from .symbols import Variable
from . import builtin
from . import symbols


MATCH_PERFECT = 3.0
MATCH_TO_VOID = 1.0


class Type:
    def fullname(self) -> str:
        raise NotImplementedError()

    def size(self):
        raise NotImplementedError()

    def resolve(self, res: 'Resolution') -> 'Type':
        raise NotImplementedError()

    def finalize(self) -> bool:
        raise NotImplementedError()


class Resolution:
    def __init__(self) -> None:
        self.generics: Dict[str, Type] = {}

    def match_unsized(self, tp: Type, other: Type) -> bool:
        if isinstance(tp, Array) and isinstance(other, Array):
            if not self.match_type(tp.type, other.type):
                return False

            return tp.length is None or tp.length == other.length

        return self.match_type(tp, other)

    def match_type(self, tp: Type, other: Type) -> bool:
        if isinstance(other, Generic):
            if isinstance(tp, Generic):
                assert False, 'what happens?'

            if other.name not in self.generics:
                self.generics[other.name] = tp
                return True

            other = self.generics[other.name]

        if isinstance(tp, Generic):
            if tp.name not in self.generics:
                self.generics[tp.name] = other
                return True

            tp = self.generics[tp.name]

        if isinstance(tp, Reference):
            return isinstance(other, Reference) \
                and tp.level == other.level \
                and self.match_unsized(tp.type, other.type)

        if isinstance(tp, Array):
            return isinstance(other, Array) \
                and tp.length == other.length \
                and self.match_type(tp.type, other.type)

        if isinstance(tp, StructType):
            if not isinstance(other, StructType):
                return False

            if tp.struct != other.struct:
                return False

            if not tp.generics.match(other.generics, self):
                return False

            return True

        if isinstance(tp, EnumerationType):
            if not isinstance(other, EnumerationType):
                return False

            if tp.enum != other.enum:
                return False

            if not tp.generics.match(other.generics, self):
                return False

            return True

        assert False, f'unknown type {tp}'

    def accept_type(self, tp: Type, other: Type) -> float:
        if other == builtin.DIVERGE:
            return MATCH_PERFECT

        if tp == builtin.UNKNOWN or other == builtin.UNKNOWN:
            return math.nan

        if tp == builtin.VOID:
            if other == builtin.VOID:
                return MATCH_PERFECT

            return MATCH_TO_VOID

        if other == builtin.VOID:
            return None

        if isinstance(other, Generic):
            if isinstance(tp, Generic):
                assert False, 'what happens?'

            if other.name not in self.generics:
                self.generics[other.name] = tp
                return MATCH_PERFECT

            other = self.generics[other.name]

        if isinstance(tp, Generic):
            if tp.name not in self.generics:
                self.generics[tp.name] = other
                return MATCH_PERFECT

            tp = self.generics[tp.name]

        if isinstance(tp, Reference):
            if not isinstance(other, Reference) \
                    or tp.level > other.level \
                    or not self.match_unsized(tp.type, other.type):
                return None

            return MATCH_PERFECT - 1.0 + tp.level / other.level

        if isinstance(other, Reference):
            # auto reduction to level 0
            other = other.type
            reduction = 1.0
        else:
            reduction = 0.0

        if isinstance(tp, (Array,
                           StructType,
                           EnumerationType)):
            if not self.match_type(tp, other):
                return None

            return MATCH_PERFECT - reduction

        assert False, f'unknown type {tp}'

    def interpolate_types(self, tps: Iterable[Type]) -> Type:
        res: Type = builtin.DIVERGE
        unknown = False
        for other in tps:
            if other == builtin.UNKNOWN:
                unknown = True
                continue

            if other == builtin.VOID:
                return builtin.VOID

            # diverge does not affect any type
            if res == builtin.DIVERGE:
                res = other
                continue
            elif other == builtin.DIVERGE:
                continue

            if isinstance(res, Reference):
                if not isinstance(other, Reference):
                    other = Reference(other, 0)

                if not self.match_type(res.type, other.type):
                    return builtin.VOID

                lvl = min(res.level, other.level)
                res = to_level(res.type, lvl)
                continue

            if isinstance(other, Reference):
                other = other.type

            if not self.match_type(res, other):
                return builtin.VOID

        if unknown:
            return builtin.UNKNOWN

        return res


class Match:
    def __init__(self,
                 source: 'symbols.SymbolTable',
                 generics: Sequence['symbols.Generic'],
                 params: Sequence['symbols.Variable'],
                 ret: Type) -> None:
        self.source = source

        self.generics = Generics(generics)
        self.params = Variables(params)
        self.ret = ret

        self.resolution: Resolution = None
        self._levels: List[float] = None
        self._resolved = False

    def __lt__(self, other: 'Match') -> bool:
        assert len(self._levels) == len(other._levels)

        # FIXME: generic has lower precedence

        less = False
        for s, o in zip(self._levels, other._levels):
            if s > o:
                return False
            if s < o:
                less = True

        return less

    def __str__(self) -> str:
        ret = f' {self.ret}' if self.ret != builtin.VOID else ''

        return f'{self.source}{self.generics}({self.params}){ret}'

    def update(self, args: List[Type], ret: Type) -> bool:
        # None: type mismatch
        # 1: casting to none
        # 2: level reduction
        # 3: exact match
        # nan: unknown

        self.resolution = Resolution()
        self._levels = self.params.accept(args, self.resolution)

        if self._levels is None:
            return False

        if ret is not None:
            lvl = self.resolution.accept_type(ret, self.ret)
        else:
            lvl = math.nan

        self._levels.append(lvl)

        return None not in self._levels

    def resolve(self) -> bool:
        assert not self._resolved

        gens = self.generics.resolve(self.resolution)
        params = self.params.resolve(self.resolution)
        ret = self.ret.resolve(self.resolution)

        if not gens.finalize():
            return False

        if not params.finalize():
            return False

        if not ret.finalize():
            return False

        self.generics = gens
        self.params = params
        self.ret = ret

        self._resolved = True
        return True


class Generics(Iterable['symbols.Generic']):
    def __init__(self, gens: Sequence['symbols.Generic']) -> None:
        self.generics = gens

    def __str__(self) -> str:
        if len(self.generics) == 0:
            return ''

        return '{' + ', '.join(str(g.type) for g in self.generics) + '}'

    def __iter__(self) -> Iterator['symbols.Generic']:
        return iter(self.generics)

    def __getitem__(self, idx: int) -> symbols.Generic:
        return self.generics[idx]

    def fullname(self) -> str:
        if len(self.generics) == 0:
            return ''

        return '{' + ','.join(g.type.fullname() for g in self.generics) + '}'

    def match(self, other: 'Generics', res: Resolution) -> bool:
        # FIXME: problematic generic matching
        for g, o in zip(self.generics, other.generics):
            if not res.match_type(g.type, o.type):
                return False

        return True

    def resolve(self, res: Resolution) -> 'Generics':
        return Generics([symbols.Generic(g.name, g.type.resolve(res))
                         for g in self.generics])

    def finalize(self) -> bool:
        for g in self.generics:
            if isinstance(g.type, Generic):
                return False

        return True

    def fill(self, gen_args: Sequence[Type]) -> 'Generics':
        return Generics([symbols.Generic(g.name, a)
                         for g, a in zip(self.generics, gen_args)])

    def create_resolution(self) -> Resolution:
        res = Resolution()
        for g in self.generics:
            res.generics[g.name] = g.type

        return res


class Variables(Iterable['symbols.Variable']):
    def __init__(self, vs: Sequence['symbols.Variable']) -> None:
        self.variables = vs

        self._size: int = None
        self._symbols: Dict[str, symbols.Variable] = None

    def __str__(self) -> str:
        return ', '.join(str(v) for v in self.variables)

    def __iter__(self) -> Iterator[Variable]:
        return iter(self.variables)

    def __getitem__(self, idx: Union[int, str]) -> Variable:
        if isinstance(idx, int):
            return self.variables[idx]

        if isinstance(idx, str):
            assert self._symbols is not None
            return self._symbols.get(idx, None)

        assert False

    def size(self) -> int:
        assert self._size is not None

        return self._size

    def accept(self,
               args: Sequence[Type],
               res: Resolution) -> List[float]:
        if len(self.variables) != len(args):
            return None

        return [res.accept_type(p.type, a)
                for p, a in zip(self.variables, args)]

    def resolve(self, res: Resolution) -> 'Variables':
        return Variables([symbols.Variable(f.name, f.type.resolve(res))
                          for f in self.variables])

    def finalize(self) -> bool:
        size = 0
        self._symbols = {}
        for field in self.variables:
            if not field.type.finalize():
                return False

            field.offset = size
            size += field.type.size()
            self._symbols[field.name] = field

        self._size = size
        return True


class Reference(Type):
    def __init__(self, tp: Type, lvl: int) -> None:
        assert not isinstance(tp, Reference)

        self.type = tp
        self.level = lvl

    def __format(self, tp: Any) -> str:
        return '&' * self.level + str(tp)

    def __str__(self) -> str:
        return self.__format(self.type)

    def fullname(self) -> str:
        return self.__format(self.type.fullname())

    def size(self) -> int:
        return 8  # size of pointer

    def resolve(self, res: Resolution) -> 'Reference':
        return Reference(self.type.resolve(res), self.level)

    def finalize(self) -> bool:
        return self.type.finalize()


class Array(Type):
    def __init__(self, tp: Type, length: int = None) -> None:
        self.type = tp
        self.length = length

    def __format(self, tp: Any, sep: str) -> str:
        length = ''
        if self.length is not None:
            length = f'{sep}{self.length}'

        return f'[{tp}{length}]'

    def __str__(self) -> str:
        return self.__format(self.type, '; ')

    def fullname(self) -> str:
        return self.__format(self.type.fullname(), ';')

    def size(self) -> int:
        if self.length is None:
            raise TypeError('array is unsized')

        return self.type.size() * self.length

    def resolve(self, res: Resolution) -> 'Array':
        return Array(self.type.resolve(res), self.length)

    def finalize(self) -> bool:
        return self.type.finalize()


class Generic(Type):
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return self.name

    def fullname(self) -> str:
        assert False, 'should not use fullname on generic'

    def size(self) -> int:
        assert False, 'should not use size on generic'

    def resolve(self, res: Resolution) -> Type:
        return res.generics.get(self.name, self)

    def finalize(self) -> bool:
        return False


class Special(Type):
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return self.name

    def fullname(self) -> str:
        assert False, 'should not use fullname on special'

    def fullpath(self) -> str:
        assert False, 'should not use fullpath on special'

    def size(self) -> int:
        assert False, 'should not use size on special'

    def resolve(self, res: Resolution) -> 'Special':
        return self

    def finalize(self) -> bool:
        return True


class StructType(Type):
    def __init__(self,
                 struct: 'symbols.Struct',
                 gens: Generics = None,
                 flds: Variables = None) -> None:
        self.struct = struct
        self.generics = gens
        self.fields = flds

        if gens is None:
            self.generics = Generics(struct.generics)

        if flds is None:
            self.fields = Variables(struct.fields)

    def __str__(self) -> str:
        return f'{self.struct}{self.generics}'

    def fullname(self) -> str:
        return f'{self.struct.fullname()}{self.generics.fullname()}'

    def size(self) -> int:
        # note: struct size is only for builtins
        return self.struct.size + self.fields.size()

    def fill(self, gen_args: Sequence[Type]) -> 'StructType':
        gens = self.generics.fill(gen_args)
        return StructType(
            self.struct,
            gens,
            self.fields.resolve(gens.create_resolution())
        )

    def resolve(self, res: Resolution) -> 'StructType':
        return StructType(
            self.struct,
            self.generics.resolve(res),
            self.fields.resolve(res)
        )

    def finalize(self) -> bool:
        if not self.generics.finalize():
            return False

        if not self.fields.finalize():
            return False

        return True


class EnumerationType(Type):
    def __init__(self,
                 enum: 'symbols.Enumeration',
                 gens: Generics = None,
                 variants: Sequence[Variables] = None) -> None:
        self.enum = enum
        self.generics = gens
        self.variants = variants

        if gens is None:
            self.generics = Generics(enum.generics)

        if variants is None:
            self.variants = [Variables(v.fields) for v in enum.variants]

    def __str__(self) -> str:
        return f'{self.enum}{self.generics}'

    def fullname(self) -> str:
        return self.enum.fullname()

    def fullpath(self) -> str:
        return self.enum.fullpath()

    def size(self) -> int:
        return self.enum.size + max(v.size() for v in self.variants)

    def fill(self, gen_args: Sequence[Type]) -> 'EnumerationType':
        gens = self.generics.fill(gen_args)
        res = gens.create_resolution()
        return EnumerationType(
            self.enum,
            gens,
            [v.resolve(res) for v in self.variants]
        )

    def resolve(self, res: Resolution) -> 'EnumerationType':
        return EnumerationType(
            self.enum,
            self.generics.resolve(res),
            [v.resolve(res) for v in self.variants]
        )

    def finalize(self) -> bool:
        if not self.generics.finalize():
            return False

        for v in self.variants:
            if not v.finalize():
                return False

        return True


def to_level(tp: Type, lvl: int) -> Type:
    assert tp is not None
    assert tp != builtin.UNKNOWN

    if isinstance(tp, Reference):
        tp = tp.type

    if lvl > 0:
        tp = Reference(tp, lvl)

    return tp


def to_ref(tp: Type) -> Reference:
    assert tp is not None
    assert tp != builtin.UNKNOWN

    if not isinstance(tp, Reference):
        tp = Reference(tp, 0)

    return tp


def resolve_overload(overloads: Set[Match],
                     args: List[Type],
                     ret: Type) -> Set[Match]:
    assert None not in args and ret is not None

    res: Set[Match] = set()

    for match in overloads:
        if not match.update(args, ret):
            continue

        res = {r for r in res if not r < match}

        for other in res:
            if match < other:
                break
        else:
            res.add(match)

    return res
