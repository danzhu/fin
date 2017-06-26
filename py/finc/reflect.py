from typing import Tuple, Dict, Any, Set, List, cast, Sequence, TypeVar
import typing
from enum import Enum
import math
from . import symbols


TTbl = TypeVar('TTbl', bound='SymbolTable')


def check_type(sym: 'Symbol', tps: Tuple[type, ...]):
    for tp in tps:
        if isinstance(sym, tp):
            return

    exp = ' or '.join(t.__name__ for t in tps)
    raise LookupError(f"expecting {exp}, but got '{sym}'")


class Location(Enum):
    Global = 0
    Struct = 1
    Enum = 2
    Param = 3
    Local = 4


class Type:
    def size(self):
        raise NotImplementedError()

    def resolve(self, gens: Dict[str, 'Type']) -> 'Type':
        raise NotImplementedError()

    def fullname(self) -> str:
        raise NotImplementedError()

    def fullpath(self) -> str:
        raise NotImplementedError()


class Symbol:
    name: str


class Callable:
    def overloads(self) -> Set['Match']:
        raise NotImplementedError()


class Variable(Symbol):
    def __init__(self,
                 name: str,
                 tp: Type,
                 loc: Location,
                 off: int = None) -> None:
        self.name = name
        self.type = tp
        self.location = loc
        self.offset = off

    def __str__(self) -> str:
        return f'{self.name} {self.type}'

    def var_type(self) -> Type:
        if not isinstance(self.type, Reference):
            return Reference(self.type, 1)

        return Reference(self.type.type, self.type.level + 1)


class Constant(Symbol):
    def __init__(self, name: str, tp: Type, val: Any) -> None:
        self.name = name
        self.type = tp
        self.value = val

    def var_type(self) -> Type:
        return self.type


class SymbolTable:
    LOCATION: Location

    def __init__(self, parent: 'SymbolTable' = None) -> None:
        self.parent = parent

        self.symbols: Dict[str, Symbol] = {}
        self.references: Dict[str, Module] = {}

    def _add_symbol(self, sym: Symbol) -> None:
        if sym.name in self.symbols:
            raise LookupError(
                f"symbol '{sym.name}' exists as {self.symbols[sym.name]}")

        self.symbols[sym.name] = sym

    def _find(self, name: str) -> Symbol:
        if name in self.symbols:
            return self.symbols[name]

        if name in self.references:
            return self.references[name]

        if self.parent:
            return self.parent._find(name)

        return None

    def _member(self, name: str) -> Symbol:
        if name in self.symbols:
            return self.symbols[name]

        return None

    def add_reference(self, mod: 'Module') -> None:
        if mod.name in self.references:
            raise LookupError(f"reference '{mod.name}' already in scope")

        self.references[mod.name] = mod

    def get(self, name: str, *tps: type) -> Symbol:
        sym = self._find(name)

        if sym is None:
            raise LookupError(f"cannot find symbol '{name}'")

        check_type(sym, tps)
        return sym

    def member(self, name: str, *tps: type) -> Symbol:
        sym = self._member(name)

        if sym is None:
            raise LookupError(f"cannot find member '{name}'")

        check_type(sym, tps)
        return sym

    def ancestor(self, tp: typing.Type[TTbl]) -> TTbl:
        if self.parent is None:
            raise LookupError(f'cannot find ancestor of type {tp.__name__}')

        if isinstance(self.parent, tp):
            return self.parent

        return self.parent.ancestor(tp)

    def module(self) -> 'Module':
        mod = self.ancestor(Module)
        assert isinstance(mod, Module)
        return mod


class Scope(Symbol, SymbolTable):
    def __str__(self):
        return self.name

    def fullname(self) -> str:
        return self.name

    def fullpath(self) -> str:
        if self.parent is None:
            return self.fullname()

        return self.module().path() + self.fullname()


class Module(Scope):
    LOCATION = Location.Global

    def __init__(self, name: str,
                 parent: 'Module',
                 builtins: 'Module' = None) -> None:
        super().__init__(parent)

        self.name = name
        self.builtins = builtins

        if parent is not None:
            parent.add_module(self)

            if builtins is None:
                self.builtins = parent.builtins

    def __lt__(self, other: 'Module') -> bool:
        return self.name < other.name

    def _find(self, name: str) -> Symbol:
        if name in self.symbols:
            return self.symbols[name]

        if name in self.references:
            return self.references[name]

        if name in self.builtins.symbols:
            return self.builtins.symbols[name]

        return None

    def path(self, sep: str = ':') -> str:
        path = self.fullpath()
        if path != '':
            path += sep

        return path

    def add_module(self, mod: 'Module') -> None:
        self._add_symbol(mod)
        mod.parent = self

    def add_struct(self, struct: 'Struct') -> None:
        self._add_symbol(struct)
        struct.parent = self

    def add_enum(self, enum: 'Enumeration') -> None:
        self._add_symbol(enum)
        enum.parent = self

    def add_function(self, fn: 'Function') -> None:
        if fn.name not in self.symbols:
            group = FunctionGroup(fn.name)
            self.symbols[fn.name] = group

        else:
            sym = self.symbols[fn.name]

            if not isinstance(sym, FunctionGroup):
                raise LookupError(f"redefining '{group}' as function")

            group = sym

        group.add(fn)
        fn.parent = self

    def add_variable(self, name: str, tp: Type) -> None:
        raise NotImplementedError()

    def add_constant(self, const: Constant) -> None:
        self._add_symbol(const)

    def operators(self, name: str) -> Set['Match']:
        ops: Set[Match]

        fns = self.symbols.get(name, None)
        if isinstance(fns, FunctionGroup):
            ops = fns.overloads()
        else:
            ops = set()

        fns = self.builtins.symbols.get(name, None)
        if isinstance(fns, FunctionGroup):
            ops |= fns.overloads()

        for ref in self.references.values():
            fns = ref.symbols.get(name, None)
            if isinstance(fns, FunctionGroup):
                ops |= fns.overloads()

        return ops


class Struct(Scope, Callable):
    LOCATION = Location.Struct

    def __init__(self, name: str, size: int = 0) -> None:
        super().__init__()

        self.name = name
        self.size = size
        self.generics: List[Generic] = []
        self.fields: List[Variable] = []

    def fullpath(self) -> str:
        return self.module().path() + self.fullname()

    def add_generic(self, name: str) -> 'Generic':
        gen = Generic(name)
        self.generics.append(gen)
        self._add_symbol(gen)
        return gen

    def add_variable(self, name: str, tp: Type) -> Variable:
        var = Variable(name, tp, Location.Struct)
        self.fields.append(var)
        self._add_symbol(var)
        return var

    def overloads(self) -> Set['Match']:
        return {Match(self, self.generics, self.fields, StructType(self))}


class Enumeration(Scope):
    LOCATION = Location.Enum

    def __init__(self, name: str) -> None:
        super().__init__()

        self.name = name

        self.size = 4
        self.counter = 0
        self.generics: List['Generic'] = []
        self.variants: List['Variant'] = []

    def __str__(self) -> str:
        return self.name

    def fullname(self) -> str:
        return self.name

    def add_generic(self, name: str) -> 'Generic':
        gen = Generic(name)
        self.generics.append(gen)
        self._add_symbol(gen)
        return gen

    def add_variant(self, name: str) -> 'Variant':
        var = Variant(name, self)
        self.counter += 1

        self._add_symbol(var)
        self.variants.append(var)
        return var


class Variant(Scope, Callable):
    LOCATION = Location.Enum

    def __init__(self, name: str, parent: Enumeration) -> None:
        super().__init__()

        self.name = name
        self.parent = parent

        self.value = parent.counter
        self.struct = Struct('<variant>', parent.size)

    def __str__(self) -> str:
        return f'{self.parent}:{self.name}'

    def add_variable(self, name: str, tp: Type) -> Variable:
        return self.struct.add_variable(name, tp)

    def overloads(self) -> Set['Match']:
        assert isinstance(self.parent, Enumeration)

        ret = EnumerationType(self.parent)
        return {Match(self, self.parent.generics, self.struct.fields, ret)}


class Function(Scope):
    LOCATION = Location.Param

    def __init__(self, name: str, ret: Type) -> None:
        super().__init__()

        self.name = name
        self.ret = ret

        self.params: List[Variable] = []
        self.generics: List[Generic] = []

    def __str__(self) -> str:
        gens = ''
        if len(self.generics) > 0:
            gens = '{' + ', '.join(str(g) for g in self.generics) + '}'

        params = ', '.join(str(p) for p in self.params)

        ret = ''
        if self.ret != symbols.VOID:
            ret = ' ' + str(self.ret)

        return f'{self.name}{gens}({params}){ret}'

    def fullname(self) -> str:
        # TODO: generic parameters
        params = ','.join(p.type.fullpath() for p in self.params)

        ret = ''
        if self.ret != symbols.VOID:
            ret = self.ret.fullpath()

        return f'{self.name}({params}){ret}'

    def add_variable(self, name: str, tp: Type) -> Variable:
        assert isinstance(name, str)

        var = Variable(name, tp, Location.Param, 0)

        self._add_symbol(var)
        self.params.append(var)

        for param in self.params:
            param.offset -= tp.size()

        return var

    def add_generic(self, name: str) -> 'Generic':
        assert isinstance(name, str)

        gen = Generic(name)

        self._add_symbol(gen)
        self.generics.append(gen)

        return gen


class FunctionGroup(Symbol):
    def __init__(self, name: str) -> None:
        self.name = name
        self.functions: Set[Function] = set()

    def __str__(self) -> str:
        return self.name

    def add(self, fn: Function) -> None:
        self.functions.add(fn)

    def overloads(self) -> Set['Match']:
        return {Match(f, f.generics, f.params, f.ret) for f in self.functions}


class Block(SymbolTable):
    LOCATION = Location.Local

    def __init__(self, parent: SymbolTable) -> None:
        super().__init__(parent)

        self.offset = 0

        if isinstance(parent, Block):
            self.parent_offset = parent.offset
        else:
            self.parent_offset = 0

    def add_variable(self, name: str, tp: Type) -> Variable:
        offset = self.parent_offset + self.offset
        var = Variable(name, tp, Location.Local, offset)
        self.offset += tp.size()

        self._add_symbol(var)
        return var


class Match:
    def __init__(self,
                 source: SymbolTable,
                 generics: Sequence['Generic'],
                 params: Sequence[Variable],
                 ret: Type) -> None:
        self.source = source

        self.generics = generics
        self.params = [p.type for p in params]
        self.ret = ret

        self.resolved_gens: Dict[str, Type] = None
        self.levels: List[float] = None

    def __lt__(self, other: 'Match') -> bool:
        assert len(self.levels) == len(other.levels)

        # generic has lower precedence
        if len(self.generics) == 0 \
                and len(other.generics) > 0:
            return False

        less = False
        for s, o in zip(self.levels, other.levels):
            if s > o:
                return False
            if s < o:
                less = True

        return less

    def __str__(self) -> str:
        gens = ''.join(f', {k} = {g}' for k, g in self.resolved_gens.items())
        # FIXME: print actual signature
        return f'{self.levels}{gens}'

    def update(self, args: List[Type], ret: Type) -> bool:
        if len(args) != len(self.params):
            return False

        # None: type mismatch
        # 1: casting to none
        # 2: level reduction
        # 3: exact match
        # nan: unknown

        self.resolved_gens = {}
        self.levels = [symbols.accept_type(p, a, self.resolved_gens)
                       for p, a in zip(self.params, args)]

        if ret is not None:
            lvl = symbols.accept_type(ret, self.ret, self.resolved_gens)
        else:
            lvl = math.nan

        self.levels.append(lvl)

        return None not in self.levels

    def resolve(self) -> bool:
        # check that all generic params are resolved
        if len(self.resolved_gens) != len(self.generics):
            return False

        self.params = [p.resolve(self.resolved_gens) for p in self.params]
        self.ret = self.ret.resolve(self.resolved_gens)
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

    def fullpath(self) -> str:
        return self.__format(self.type.fullpath())

    def size(self) -> int:
        return 8  # size of pointer

    def resolve(self, gens: Dict[str, Type]) -> 'Reference':
        return Reference(self.type.resolve(gens), self.level)


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

    def fullpath(self) -> str:
        return self.__format(self.type.fullpath(), ';')

    def size(self) -> int:
        if self.length is None:
            raise TypeError('array is unsized')

        return self.type.size() * self.length

    def resolve(self, gens: Dict[str, Type]) -> 'Array':
        return Array(self.type.resolve(gens))


class Generic(Type, Symbol):
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return self.name

    def fullname(self) -> str:
        assert False, 'should not use fullname on generic'

    def fullpath(self) -> str:
        assert False, 'should not use fullpath on generic'

    def size(self) -> int:
        assert False, 'should not use size on generic'

    def resolve(self, gens: Dict[str, Type]) -> Type:
        return gens[self.name]


class StructType(Type):
    def __init__(self,
                 struct: Struct,
                 fields: List[Variable] = None,
                 gens: List[Type] = None) -> None:
        self.struct = struct
        self.fields = fields
        self.generics = gens

        if self.fields is None:
            self.fields = struct.fields

        if self.generics is None:
            self.generics = cast(List[Type], struct.generics)

        self._finalized = False
        self.symbols: Dict[str, Variable] = None

    def __str__(self) -> str:
        res = str(self.struct)
        if len(self.generics) > 0:
            res += '{' + ', '.join(str(g) for g in self.generics) + '}'

        return res

    def fullname(self) -> str:
        res = self.struct.fullname()
        if len(self.generics) > 0:
            res += '{' + ','.join(g.fullname() for g in self.generics) + '}'

        return res

    def fullpath(self) -> str:
        res = self.struct.fullpath()
        if len(self.generics) > 0:
            res += '{' + ','.join(g.fullpath() for g in self.generics) + '}'

        return res

    def member(self, name: str) -> Variable:
        self.finalize()

        if name not in self.symbols:
            raise LookupError(
                f"field '{name}' does not exist in struct '{self.struct}'")

        return self.symbols[name]

    def size(self) -> int:
        self.finalize()

        # note: struct size is only for builtins
        return self.struct.size + sum(f.type.size() for f in self.fields)

    def resolve(self, gens: Dict[str, Type]) -> 'StructType':
        fields = []
        for f in self.fields:
            var = Variable(f.name, f.type.resolve(gens), Location.Struct)
            fields.append(var)

        gen_args = []
        for g in self.generics:
            if isinstance(g, Generic):
                g = g.resolve(gens)

            gen_args.append(g)

        return StructType(self.struct, fields, gen_args)

    def finalize(self) -> None:
        if self._finalized:
            return

        size = 0
        self.symbols = {}
        for f in self.fields:
            f.offset = size
            size += f.type.size()
            self.symbols[f.name] = f

        self._finalized = True


class EnumerationType(Type):
    def __init__(self,
                 enum: Enumeration,
                 variants: Sequence[StructType] = None,
                 gens: Sequence[Type] = None) -> None:
        super().__init__()

        self.enum = enum
        self.variants = variants
        self.generics = gens

        if self.variants is None:
            self.variants = [StructType(v.struct) for v in enum.variants]

        if self.generics is None:
            self.generics = enum.generics

    def __str__(self) -> str:
        return str(self.enum)

    def fullname(self) -> str:
        return self.enum.fullname()

    def fullpath(self) -> str:
        return self.enum.fullpath()

    def size(self) -> int:
        return max(v.size() for v in self.variants)

    def resolve(self, gens: Dict[str, Type]) -> 'EnumerationType':
        variants = [v.resolve(gens) for v in self.variants]
        gen_args = []
        for g in self.generics:
            if isinstance(g, Generic):
                g = g.resolve(gens)

            gen_args.append(g)

        return EnumerationType(self.enum, variants, gen_args)


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

    def resolve(self, gens: Dict[str, Type]) -> 'Special':
        return self
