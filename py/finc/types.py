from typing import Any, Sequence, List, Dict, Iterator, Iterable, Union, Set, \
    Sized
import math
from . import builtin
from . import symbols


MATCH_PERFECT = 3.0
MATCH_TO_VOID = 1.0


class Type:
    def __eq__(self, other: object) -> bool:
        raise NotImplementedError()

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def fullname(self) -> str:
        raise NotImplementedError()

    def resolve(self, res: 'Resolution') -> 'Type':
        raise NotImplementedError()


class Resolution:
    def __init__(self) -> None:
        self.generics: Dict[str, Type] = {}

    def resolved(self) -> bool:
        return None not in self.generics.values()

    def match_unsized(self, tp: Type, other: Type, ret: bool) -> bool:
        assert tp is not None
        assert other is not None

        if isinstance(tp, Array) and isinstance(other, Array):
            if not self.match_type(tp.type, other.type, ret):
                return False

            return tp.length is None or tp.length == other.length

        return self.match_type(tp, other, ret)

    def match_type(self, tp: Type, other: Type, ret: bool) -> bool:
        # ret = if matching return type. In this case 'other' is checked for
        # generics instead of 'tp'

        assert tp is not None
        assert other is not None

        if not ret and isinstance(tp, Generic) and tp.name in self.generics:
            if self.generics[tp.name] is None:
                self.generics[tp.name] = other
                return True

            tp = self.generics[tp.name]

        if ret and isinstance(other, Generic) and other.name in self.generics:
            if self.generics[other.name] is None:
                self.generics[other.name] = tp
                return True

            other = self.generics[other.name]

        if isinstance(tp, Reference):
            return isinstance(other, Reference) \
                and self.match_unsized(tp.type, other.type, ret)

        if isinstance(tp, Array):
            return isinstance(other, Array) \
                and tp.length == other.length \
                and self.match_type(tp.type, other.type, ret)

        if isinstance(tp, (StructType, EnumerationType)):
            if not isinstance(other, type(tp)):
                return False

            # silence type check error
            assert isinstance(other, (StructType, EnumerationType))

            if tp.symbol != other.symbol:
                return False

            if not tp.generics.match(other.generics, self, ret):
                return False

            return True

        if isinstance(tp, Generic):
            if not isinstance(other, Generic):
                return False

            if tp.name != other.name:
                return False

            return True

        assert False, f'unknown type {tp}'

    def accept_type(self, tp: Type, other: Type, ret: bool) -> float:
        assert tp is not None
        assert other is not None

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

        if not ret and isinstance(tp, Generic) and tp.name in self.generics:
            if self.generics[tp.name] is None:
                self.generics[tp.name] = other
                return MATCH_PERFECT

            tp = self.generics[tp.name]

        if ret and isinstance(other, Generic) and other.name in self.generics:
            if self.generics[other.name] is None:
                self.generics[other.name] = tp
                return MATCH_PERFECT

            other = self.generics[other.name]

        if isinstance(tp, Reference):
            # cannot cast from non-reference to reference
            if not isinstance(other, Reference):
                return None

            # remove common references
            while isinstance(tp, Reference) and isinstance(other, Reference):
                tp = tp.type
                other = other.type

            reduction = 0.0

            while isinstance(other, Reference):
                other = other.type
                reduction = 1.0

            if not self.match_unsized(tp, other, ret):
                return None

            return MATCH_PERFECT - reduction

        if isinstance(other, Reference):
            # auto reduction to level 0
            other = other.type
            reduction = 1.0
        else:
            reduction = 0.0

        if isinstance(tp, Array):
            # using unsized array is not allowed
            if tp.length is None:
                return None

            if not self.match_type(tp, other, ret):
                return None

            return MATCH_PERFECT - reduction

        if isinstance(tp, (StructType, EnumerationType, Generic)):
            if not self.match_type(tp, other, ret):
                return None

            return MATCH_PERFECT - reduction

        assert False, f'unknown type {tp}'

    def interpolate_types(self, tps: Iterable[Type]) -> Type:
        res: Type = builtin.DIVERGE
        unknown = False
        for other in tps:
            if other == builtin.VOID:
                return builtin.VOID

            if other == builtin.UNKNOWN:
                unknown = True
                continue

            # diverge does not affect any type
            if res == builtin.DIVERGE:
                res = other
                continue

            if other == builtin.DIVERGE:
                continue

            if isinstance(res, Reference):
                left: Type = res
                right: Type = other
                lvl = 0
                while isinstance(left, Reference) and \
                        isinstance(right, Reference):
                    left = left.type
                    right = right.type
                    lvl += 1

                # use the size that accepts implicit conversion from the other
                if self.match_type(left, right, True):
                    tp = left
                elif self.match_type(right, left, True):
                    tp = right
                else:
                    # cannot match
                    return builtin.VOID

                for _ in range(lvl):
                    tp = Reference(tp)

                res = tp
                continue

            if isinstance(other, Reference):
                other = other.type

            # FIXME: generics problems?
            if not self.match_type(res, other, False):
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

    def __repr__(self) -> str:
        return f'{self} {self._levels}'

    def update(self, args: Sequence[Type], ret: Type) -> bool:
        # None: type mismatch
        # 1: casting to none
        # 2: level reduction
        # 3: exact match
        # nan: unknown

        self.resolution = self.generics.resolution()
        self._levels = self.params.accept(args, self.resolution)

        # for incorrect number of arguments
        if self._levels is None:
            return False

        if ret is not None:
            lvl = self.resolution.accept_type(ret, self.ret, True)
        else:
            lvl = math.nan

        self._levels.append(lvl)

        return None not in self._levels

    def resolve(self) -> bool:
        assert not self._resolved

        if not self.resolution.resolved():
            return False

        self.generics = self.generics.resolve(self.resolution)
        self.params = self.params.resolve(self.resolution)
        self.ret = self.ret.resolve(self.resolution)

        self._resolved = True
        return True


class Generics(Iterable[Type], Sized):
    def __init__(self,
                 gens: Sequence['symbols.Generic'],
                 args: Sequence[Type] = None) -> None:
        self.generics = gens
        self.args = args

        if args is not None:
            assert len(gens) == len(args)
            self._resolved = True
        else:
            self.args = [Generic(g) for g in gens]
            self._resolved = len(gens) == 0

    def __str__(self) -> str:
        if len(self.generics) == 0:
            return ''

        lst: Sequence[Any]
        if self._resolved:
            lst = self.args
        else:
            lst = self.generics

        return '{' + ', '.join(str(a) for a in lst) + '}'

    def __iter__(self) -> Iterator[Type]:
        assert self._resolved
        return iter(self.args)

    def __getitem__(self, idx: int) -> Type:
        assert self._resolved
        return self.args[idx]

    def __len__(self) -> int:
        return len(self.generics)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Generics):
            return False

        return self.args == other.args

    def fullname(self) -> str:
        assert self._resolved

        if len(self.generics) == 0:
            return ''

        return '{' + ','.join(a.fullname() for a in self.args) + '}'

    def match(self, other: 'Generics', res: Resolution, ret: bool) -> bool:
        if len(self.generics) != len(other.generics):
            return False

        # FIXME: problematic generic matching
        for i in range(len(self.generics)):
            if not ret and isinstance(self.args[i], Generic):
                res.generics[self.generics[i].name] = other.args[i]
                continue

            if ret and isinstance(other.args[i], Generic):
                res.generics[other.generics[i].name] = self.args[i]
                continue

            if not res.match_type(self.args[i], other.args[i], ret):
                return False

        return True

    def resolve(self, res: Resolution) -> 'Generics':
        return Generics(self.generics, [a.resolve(res) for a in self.args])

    def resolution(self) -> Resolution:
        res = Resolution()
        if self._resolved:
            for gen, arg in zip(self.generics, self.args):
                res.generics[gen.name] = arg
        else:
            for gen in self.generics:
                res.generics[gen.name] = None

        return res


class Variables(Iterable['symbols.Variable'], Sized):
    def __init__(self, vs: Sequence['symbols.Variable']) -> None:
        self.variables = vs

        self._symbols = {var.name: var for var in vs}

    def __str__(self) -> str:
        return ', '.join(str(v) for v in self.variables)

    def __iter__(self) -> Iterator['symbols.Variable']:
        return iter(self.variables)

    def __getitem__(self, idx: Union[int, str]) -> 'symbols.Variable':
        if isinstance(idx, int):
            return self.variables[idx]

        if isinstance(idx, str):
            return self._symbols.get(idx, None)

        assert False

    def __len__(self) -> int:
        return len(self.variables)

    def accept(self,
               args: Sequence[Type],
               res: Resolution) -> List[float]:
        if len(self.variables) != len(args):
            return None

        return [res.accept_type(p.type, a, False)
                for p, a in zip(self.variables, args)]

    def resolve(self, res: Resolution) -> 'Variables':
        return Variables([symbols.Variable(f.name,
                                           f.type.resolve(res),
                                           f.index,
                                           f.is_arg)
                          for f in self.variables])


class Reference(Type):
    def __init__(self, tp: Type) -> None:
        self.type = tp

    def __format(self, tp: Any) -> str:
        return '&' + str(tp)

    def __str__(self) -> str:
        return self.__format(self.type)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Reference):
            return False

        return self.type == other.type

    def fullname(self) -> str:
        return self.__format(self.type.fullname())

    def resolve(self, res: Resolution) -> 'Reference':
        tp = self.type.resolve(res)
        return Reference(tp)


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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Array):
            return False

        return self.type == other.type and self.length == other.length

    def fullname(self) -> str:
        return self.__format(self.type.fullname(), ';')

    def resolve(self, res: Resolution) -> 'Array':
        tp = self.type.resolve(res)
        return Array(tp, self.length)


class Generic(Type):
    def __init__(self, sym: symbols.Generic) -> None:
        self.name = sym.name
        self.symbol = sym

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Generic):
            return False

        return self.symbol is other.symbol

    def fullname(self) -> str:
        return self.symbol.fullname()

    def resolve(self, res: Resolution) -> Type:
        return res.generics.get(self.name, self)


class Special(Type):
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        return self is other

    def fullname(self) -> str:
        return self.name

    def resolve(self, res: Resolution) -> 'Special':
        return self


class StructType(Type):
    def __init__(self,
                 struct: 'symbols.Struct',
                 gens: Generics = None,
                 flds: Variables = None) -> None:
        self.symbol = struct
        self.generics = gens
        self.fields = flds

        if gens is None:
            self.generics = Generics(struct.generics)

        if flds is None:
            self.fields = Variables(struct.fields)
            if gens is not None:
                self.fields = self.fields.resolve(gens.resolution())

    def __str__(self) -> str:
        return f'{self.symbol}{self.generics}'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StructType):
            return False

        if self.symbol is not other.symbol:
            return False

        if self.generics != other.generics:
            return False

        return True

    def fullname(self) -> str:
        return f'{self.symbol.fullname()}{self.generics.fullname()}'

    def resolve(self, res: Resolution) -> 'StructType':
        gens = self.generics.resolve(res)
        return StructType(
            self.symbol,
            gens,
            self.fields.resolve(res)
        )


class EnumerationType(Type):
    def __init__(self,
                 enum: 'symbols.Enumeration',
                 gens: Generics = None,
                 variants: Sequence[Variables] = None) -> None:
        self.symbol = enum
        self.generics = gens
        self.variants = variants

        if gens is None:
            self.generics = Generics(enum.generics)

        if variants is None:
            self.variants = [Variables(v.fields) for v in enum.variants]
            if gens is not None:
                res = gens.resolution()
                self.variants = [v.resolve(res) for v in self.variants]

    def __str__(self) -> str:
        return f'{self.symbol}{self.generics}'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EnumerationType):
            return False

        if self.symbol is not other.symbol:
            return False

        if self.generics != other.generics:
            return False

        return True

    def fullname(self) -> str:
        return self.symbol.fullname()

    def resolve(self, res: Resolution) -> 'EnumerationType':
        gens = self.generics.resolve(res)
        return EnumerationType(
            self.symbol,
            gens,
            [v.resolve(res) for v in self.variants]
        )


def deref(tp: Type) -> Type:
    assert tp is not None
    assert tp != builtin.UNKNOWN

    if not isinstance(tp, Reference):
        raise TypeError(f'cannot dereference {tp}')

    return tp.type


def remove_ref(tp: Type) -> Type:
    assert tp is not None
    assert tp != builtin.UNKNOWN

    while isinstance(tp, Reference):
        tp = tp.type

    return tp


def resolve_overload(overloads: Set[Match],
                     args: Sequence[Type],
                     ret: Type) -> Set[Match]:
    assert None not in args, f'None in {args}'
    assert ret is not None, f'{ret} == None'

    res: Set[Match] = set()

    for match in overloads:
        succ = match.update(args, ret)

        if not succ:
            continue

        res = {r for r in res if not r < match}

        for other in res:
            if match < other:
                break
        else:
            res.add(match)

    return res
