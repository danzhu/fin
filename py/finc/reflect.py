from typing import Tuple, Dict, Any, Set, List, cast, Sequence, TypeVar
import typing
import math
from . import symbols


TTbl = TypeVar('TTbl', bound='SymbolTable')


def check_type(sym: 'Symbol', tps: Tuple[type, ...]):
    for tp in tps:
        if isinstance(sym, tp):
            return

    exp = ' or '.join(t.__name__ for t in tps)
    raise LookupError(f"expecting {exp}, but got {type(sym).__name__} '{sym}'")


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


class Invokable:
    def overloads(self) -> Set['Match']:
        raise NotImplementedError()


class SymbolTable:
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


class Constant(Symbol):
    def __init__(self, name: str, tp: Type, val: Any) -> None:
        self.name = name
        self.type = tp
        self.value = val

    def var_type(self) -> Type:
        return self.type


class Variable(Symbol):
    def __init__(self,
                 name: str,
                 tp: Type,
                 off: int) -> None:
        self.name = name
        self.type = tp
        self.offset = off

    def __str__(self) -> str:
        return f'{self.name} {self.type}'

    def var_type(self) -> Type:
        lvl = self.type.level if isinstance(self.type, Reference) else 0
        return symbols.to_level(self.type, lvl + 1)


class Field(Symbol):
    def __init__(self,
                 name: str,
                 tp: Type) -> None:
        self.name = name
        self.type = tp

    def __str__(self) -> str:
        return f'{self.name} {self.type}'


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


class Struct(Scope, Invokable):
    def __init__(self, name: str, size: int = 0) -> None:
        super().__init__()

        self.name = name
        self.size = size
        self.generics: List[Generic] = []
        self.fields: List[Field] = []

    def add_generic(self, name: str) -> 'Generic':
        gen = Generic(name)
        self.generics.append(gen)
        self._add_symbol(gen)
        return gen

    def add_field(self, name: str, tp: Type) -> Field:
        field = Field(name, tp)
        self.fields.append(field)
        self._add_symbol(field)
        return field

    def overloads(self) -> Set['Match']:
        return {Match(self, self.generics, self.fields, StructType(self))}


class Enumeration(Scope):
    def __init__(self, name: str) -> None:
        super().__init__()

        self.name = name

        self.size = 4
        self.counter = 0
        self.generics: List['Generic'] = []
        self.variants: List['Variant'] = []

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


class Variant(Scope, Invokable):
    def __init__(self, name: str, parent: Enumeration) -> None:
        super().__init__()

        assert isinstance(parent, Enumeration)

        self.name = name
        self.parent = parent
        self.enum = parent

        self.value = parent.counter
        self.struct = Struct('<variant>', parent.size)

    def __str__(self) -> str:
        return f'{self.parent}:{self.name}'

    def add_field(self, name: str, tp: Type) -> Field:
        field = self.struct.add_field(name, tp)
        self._add_symbol(field)
        return field

    def overloads(self) -> Set['Match']:
        ret = EnumerationType(self.enum)
        return {Match(self, self.enum.generics, self.struct.fields, ret)}


class Function(Scope):
    def __init__(self, name: str, ret: Type) -> None:
        super().__init__()

        self.name = name
        self.ret = ret

        self.params: List[Field] = []
        self.generics: List[Generic] = []

    def fullname(self) -> str:
        # TODO: generic parameters
        params = ','.join(p.type.fullpath() for p in self.params)

        ret = ''
        if self.ret != symbols.VOID:
            ret = self.ret.fullpath()

        return f'{self.name}({params}){ret}'

    def add_param(self, name: str, tp: Type) -> Field:
        assert isinstance(name, str)

        param = Field(name, tp)

        self._add_symbol(param)
        self.params.append(param)
        return param

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
    def __init__(self, parent: SymbolTable, offset: int) -> None:
        super().__init__(parent)

        self.offset = offset

    def add_local(self, name: str, tp: Type) -> Variable:
        var = Variable(name, tp, self.offset)
        self.offset += tp.size()

        self._add_symbol(var)
        return var


class Match:
    def __init__(self,
                 source: SymbolTable,
                 generics: Sequence['Generic'],
                 params: Sequence[Field],
                 ret: Type) -> None:
        self.source = source

        self._generics = generics
        self._params = params
        self._ret = ret

        self.resolved_gens: Dict[str, Type] = None
        self.args: List[Type] = None
        self.result: Type = None

        self._levels: List[float] = None
        self._resolved = False

    def __lt__(self, other: 'Match') -> bool:
        assert len(self._levels) == len(other._levels)

        # generic has lower precedence
        if len(self._generics) == 0 \
                and len(other._generics) > 0:
            return False

        less = False
        for s, o in zip(self._levels, other._levels):
            if s > o:
                return False
            if s < o:
                less = True

        return less

    def __str__(self) -> str:
        if len(self._generics) > 0:
            gens = '{'
            for g in self._generics:
                gens += g.name
                resolved = self.resolved_gens.get(g.name, None)
                if resolved is not None:
                    gens += f'={resolved}'

            gens += '}'
        else:
            gens = ''

        params = ', '.join(str(p) for p in self._params)

        ret = f' {self._ret}' if self._ret != symbols.VOID else ''

        return f'{self.source}{gens}({params}){ret} {self._levels}'

    def update(self, args: List[Type], ret: Type) -> bool:
        if len(args) != len(self._params):
            return False

        # None: type mismatch
        # 1: casting to none
        # 2: level reduction
        # 3: exact match
        # nan: unknown

        self.resolved_gens = {}
        self._levels = [symbols.accept_type(p.type, a, self.resolved_gens)
                        for p, a in zip(self._params, args)]

        if ret is not None:
            lvl = symbols.accept_type(ret, self._ret, self.resolved_gens)
        else:
            lvl = math.nan

        self._levels.append(lvl)

        return None not in self._levels

    def resolve(self) -> bool:
        assert not self._resolved
        # check that all generic params are resolved
        if len(self.resolved_gens) != len(self._generics):
            return False

        self.args = [p.type.resolve(self.resolved_gens) for p in self._params]
        self.result = self._ret.resolve(self.resolved_gens)

        self._resolved = True
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
                 fields: List[Field] = None,
                 gens: List[Type] = None) -> None:
        self.struct = struct
        self.fields = fields
        self.generics = gens

        if self.fields is None:
            self.fields = struct.fields

        if self.generics is None:
            self.generics = cast(List[Type], struct.generics)

        self._finalized = False
        self.resolved_fields: List[Variable] = None
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

    def field(self, name: str) -> Variable:
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
            field = Field(f.name, f.type.resolve(gens))
            fields.append(field)

        gen_args = []
        for g in self.generics:
            if isinstance(g, Generic):
                g = g.resolve(gens)

            gen_args.append(g)

        return StructType(self.struct, fields, gen_args)

    def finalize(self) -> None:
        if self._finalized:
            return

        size = self.struct.size
        self.resolved_fields = []
        self.symbols = {}
        for f in self.fields:
            var = Variable(f.name, f.type, size)
            size += f.type.size()

            self.resolved_fields.append(var)
            self.symbols[f.name] = var

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
