from typing import Tuple, Dict, Any, Set, List, TypeVar
import typing
from . import types
from . import builtin


TTbl = TypeVar('TTbl', bound='SymbolTable')


def check_type(sym: 'Symbol', tps: Tuple[type, ...]):
    for tp in tps:
        if isinstance(sym, tp):
            return

    exp = ' or '.join(t.__name__ for t in tps)
    raise LookupError(f"expecting {exp}, but got {type(sym).__name__} '{sym}'")


class Symbol:
    name: str


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
    def __init__(self, name: str, tp: 'types.Type', val: Any) -> None:
        self.name = name
        self.type = tp
        self.value = val

    def var_type(self) -> 'types.Type':
        return self.type


class Variable(Symbol):
    def __init__(self,
                 name: str,
                 tp: 'types.Type',
                 is_arg: bool = False) -> None:
        self.name = name
        self.type = tp
        self.is_arg = is_arg

    def __str__(self) -> str:
        return f'{self.name} {self.type}'

    def var_type(self) -> 'types.Type':
        if isinstance(self.type, types.Reference):
            lvl = self.type.level
        else:
            lvl = 0

        return types.to_level(self.type, lvl + 1)


class Generic(Symbol):
    def __init__(self, name: str, idx: int) -> None:
        self.name = name
        self.index = idx

    def __str__(self) -> str:
        return self.name

    def fullname(self) -> str:
        return str(self.index)


class Scope(Symbol, SymbolTable):
    def __str__(self):
        return self.name

    def fullname(self) -> str:
        if self.parent is None:
            return self.basename()

        return self.module().path() + self.basename()

    def basename(self) -> str:
        raise NotImplementedError()


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

    def basename(self) -> str:
        return self.name

    def path(self, sep: str = ':') -> str:
        path = self.fullname()
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
                raise LookupError(f"redefining '{sym}' as function")

            group = sym

        group.add(fn)
        fn.parent = self

    def add_variable(self, name: str, tp: 'types.Type') -> None:
        assert False, 'TODO'

    def add_constant(self, const: Constant) -> None:
        self._add_symbol(const)

    def operators(self, name: str) -> Set['types.Match']:
        ops: Set[types.Match]

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


class Struct(Scope):
    def __init__(self, name: str, size: int = 0) -> None:
        super().__init__()

        self.name = name
        self.size = size
        self.generics: List[Generic] = []
        self.fields: List[Variable] = []

    def basename(self) -> str:
        return self.name

    def add_generic(self, name: str) -> Generic:
        gen = Generic(name, len(self.generics))
        self.generics.append(gen)
        self._add_symbol(gen)
        return gen

    def add_field(self, name: str, tp: 'types.Type') -> Variable:
        field = Variable(name, tp)
        self.fields.append(field)
        self._add_symbol(field)
        return field

    def overloads(self) -> Set['types.Match']:
        ret = types.StructType(self)
        return {types.Match(self, self.generics, self.fields, ret)}


class Enumeration(Scope):
    def __init__(self, name: str) -> None:
        super().__init__()

        self.name = name

        self.size = 4
        self.counter = 0
        self.generics: List['Generic'] = []
        self.variants: List['Variant'] = []

    def basename(self) -> str:
        return self.name

    def add_generic(self, name: str) -> 'Generic':
        gen = Generic(name, len(self.generics))
        self.generics.append(gen)
        self._add_symbol(gen)
        return gen

    def add_variant(self, name: str) -> 'Variant':
        var = Variant(name, self)
        self.counter += 1

        self._add_symbol(var)
        self.variants.append(var)
        return var


class Variant(Scope):
    def __init__(self, name: str, parent: Enumeration) -> None:
        super().__init__()

        self.name = name
        self.parent = parent
        self.enum = parent

        self.value = parent.counter
        self.fields: List[Variable] = []

    def __str__(self) -> str:
        return f'{self.parent}:{self.name}'

    def basename(self) -> str:
        return f'{self.enum.name}:{self.name}'

    def add_field(self, name: str, tp: 'types.Type') -> Variable:
        field = Variable(name, tp)
        self.fields.append(field)
        self._add_symbol(field)
        return field

    def overloads(self) -> Set['types.Match']:
        ret = types.EnumerationType(self.enum)
        return {types.Match(self, self.enum.generics, self.fields, ret)}


class Function(Scope):
    def __init__(self, name: str) -> None:
        super().__init__()

        self.name = name

        self.ret: types.Type = None
        self.params: List[Variable] = []
        self.generics: List[Generic] = []

    def __lt__(self, other: 'Function') -> bool:
        return self.module() < other.module() and self.name < other.name

    def basename(self) -> str:
        params = ','.join(p.type.fullname() for p in self.params)
        ret = self.ret.fullname() if self.ret != builtin.VOID else ''

        return f'{self.name}({params}){ret}'

    def add_param(self, name: str, tp: 'types.Type') -> Variable:
        param = Variable(name, tp, is_arg=True)

        self._add_symbol(param)
        self.params.append(param)
        return param

    def add_generic(self, name: str) -> 'Generic':
        gen = Generic(name, len(self.generics))

        self._add_symbol(gen)
        self.generics.append(gen)
        return gen

    def set_ret(self, ret: 'types.Type') -> None:
        self.ret = ret


class FunctionGroup(Symbol):
    def __init__(self, name: str) -> None:
        self.name = name
        self.functions: Set[Function] = set()

    def __str__(self) -> str:
        return self.name

    def add(self, fn: Function) -> None:
        self.functions.add(fn)

    def overloads(self) -> Set['types.Match']:
        return {types.Match(f, f.generics, f.params, f.ret)
                for f in self.functions}


class Block(SymbolTable):
    def __init__(self, parent: SymbolTable) -> None:
        super().__init__(parent)

        self.locals: List[Variable] = []

    def add_local(self, name: str, tp: 'types.Type') -> Variable:
        var = Variable(name, tp)
        self.locals.append(var)
        self._add_symbol(var)
        return var
