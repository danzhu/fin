import typing
from . import symbols
from . import builtin
from . import types
from . import pattern
from . import tokens


TNode = typing.TypeVar('TNode', bound='Node')


class Node:
    def __init__(self) -> None:
        self.start_token: tokens.Token = None
        self.end_token: tokens.Token = None

    def __str__(self) -> str:
        return type(self).__name__

    def __repr__(self) -> str:
        return ' '.join(str(e) for e in self._detail() if e is not None)

    def _detail(self) -> typing.List[object]:
        return [self.__class__.__name__]

    def set_loc(self, start: tokens.Token, end: tokens.Token) -> None:
        self.start_token = start
        self.end_token = end

    def children(self) -> typing.Iterable['Node']:
        raise NotImplementedError()

    def print(self, indent: int = 0) -> None:
        print('  ' * indent + repr(self))
        for c in self.children():
            if c is not None:
                c.print(indent + 1)

    def decedents(self, tp: typing.Type[TNode]) -> typing.Set[TNode]:
        res: typing.Set[TNode] = set()
        for c in self.children():
            if isinstance(c, tp):
                res.add(c)

            if c is not None:
                res |= c.decedents(tp)

        return res


# --- base classes ---

class Decl(Node):
    def children(self) -> typing.Iterable[Node]:
        raise NotImplementedError()


class Type(Node):
    def children(self) -> typing.Iterable[Node]:
        raise NotImplementedError()


class Pattern(Node):
    def children(self) -> typing.Iterable[Node]:
        raise NotImplementedError()


class Expr(Node):
    def __init__(self) -> None:
        Node.__init__(self)

        self.expr_type: types.Type = None

    def _detail(self) -> typing.List[object]:
        return Node._detail(self) + (
            [f'<{self.expr_type}>']
            if self.expr_type is not None
            else [])

    def children(self) -> typing.Iterable[Node]:
        raise NotImplementedError()


class List(typing.Generic[TNode], typing.Iterable[TNode], typing.Sized, Node):
    def __init__(self, items: typing.List[TNode]) -> None:
        Node.__init__(self)

        self.items = items

    def __iter__(self) -> typing.Iterator[TNode]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    @typing.overload
    def __getitem__(self, key: int) -> TNode:
        pass

    @typing.overload
    def __getitem__(self, key: slice) -> typing.Sequence[TNode]:
        pass

    def __getitem__(self, key):
        return self.items[key]

    def __setitem__(self, key: int, val: TNode) -> None:
        self.items[key] = val

    def children(self) -> typing.Iterable[Node]:
        return self.items


# --- basic classes ---

class File(List[Decl]):
    pass


class Path(Node):
    def __init__(self,
                 path: 'Path',
                 name: str) -> None:
        Node.__init__(self)

        self.path = path
        self.name = name

    def _detail(self) -> typing.List[object]:
        return Node._detail(self) + [self.name]

    def children(self) -> typing.Iterable[Node]:
        return [self.path]


class Generic(Node):
    def __init__(self,
                 name: str) -> None:
        Node.__init__(self)

        self.name = name

    def _detail(self) -> typing.List[object]:
        return Node._detail(self) + [self.name]

    def children(self) -> typing.Iterable[Node]:
        return []


class Param(Node):
    def __init__(self,
                 name: str,
                 tp: Type) -> None:
        Node.__init__(self)

        self.name = name
        self.type = tp

    def _detail(self) -> typing.List[object]:
        return Node._detail(self) + [self.name]

    def children(self) -> typing.Iterable[Node]:
        return [self.type]


class Field(Node):
    def __init__(self,
                 name: str,
                 tp: Type) -> None:
        Node.__init__(self)

        self.name = name
        self.type = tp

    def _detail(self) -> typing.List[object]:
        return Node._detail(self) + [self.name]

    def children(self) -> typing.Iterable[Node]:
        return [self.type]


class Arm(Node):
    def __init__(self,
                 pat: Pattern,
                 cont: Expr) -> None:
        Node.__init__(self)

        self.pattern = pat
        self.content = cont

        self.target: Match = None
        self.pat: pattern.Pattern = None

    def _detail(self) -> typing.List[object]:
        return Node._detail(self) + [self.target, self.pat]

    def children(self) -> typing.Iterable[Node]:
        return [self.pattern, self.content]


class Variant(Node):
    def __init__(self,
                 name: str,
                 flds: List[Field]) -> None:
        Node.__init__(self)

        self.name = name
        self.fields = flds

    def _detail(self) -> typing.List[object]:
        return Node._detail(self) + [self.name]

    def children(self) -> typing.Iterable[Node]:
        return [self.fields]


# --- declaration nodes ---

class Import(Decl):
    def __init__(self,
                 path: Path) -> None:
        Decl.__init__(self)

        self.path = path

    def children(self) -> typing.Iterable[Node]:
        return [self.path]


class Def(Decl):
    def __init__(self,
                 name: str,
                 gens: List[Generic],
                 params: List[Param],
                 ret: Type,
                 body: Expr) -> None:
        Decl.__init__(self)

        self.name = name
        self.generics = gens
        self.parameters = params
        self.return_type = ret
        self.body = body

        self.symbol: symbols.Function = None

    def _detail(self) -> typing.List[object]:
        content = self.name
        if self.symbol is not None:
            if len(self.symbol.generics) > 0:
                content += '{' + \
                    ', '.join(str(gen) for gen in self.symbol.generics) + \
                    '}'

            content += '(' + \
                ', '.join(str(par) for par in self.symbol.params) + \
                ')'

            if self.symbol.ret != builtin.VOID:
                content += f' {self.symbol.ret}'

        return Decl._detail(self) + [content]

    def children(self) -> typing.Iterable[Node]:
        return [self.generics, self.parameters, self.return_type, self.body]


class Struct(Decl):
    def __init__(self,
                 name: str,
                 gens: List[Generic],
                 flds: List[Field]) -> None:
        Decl.__init__(self)

        self.name = name
        self.generics = gens
        self.fields = flds

        self.symbol: symbols.Struct = None

    def _detail(self) -> typing.List[object]:
        content = self.name
        if self.symbol is not None:
            content += f' {self.symbol}'

        return Decl._detail(self) + [content]

    def children(self) -> typing.Iterable[Node]:
        return [self.generics, self.fields]


class Enum(Decl):
    def __init__(self,
                 name: str,
                 gens: List[Generic],
                 vrts: List[Variant]) -> None:
        Decl.__init__(self)

        self.name = name
        self.generics = gens
        self.variants = vrts

        self.symbol: symbols.Enumeration = None

    def _detail(self) -> typing.List[object]:
        content = self.name
        if self.symbol is not None:
            content += f' {self.symbol}'

        return Decl._detail(self) + [content]

    def children(self) -> typing.Iterable[Node]:
        return [self.generics, self.variants]


# --- type nodes ---

class TypeRef(Type):
    def __init__(self,
                 tp: Type) -> None:
        Type.__init__(self)

        self.type = tp

    def children(self) -> typing.Iterable[Node]:
        return [self.type]


class TypeArray(Type):
    def __init__(self,
                 tp: Type,
                 leng: 'Const') -> None:
        Type.__init__(self)

        self.type = tp
        self.length = leng

    def children(self) -> typing.Iterable[Node]:
        return [self.type, self.length]


class TypeNamed(Type):
    def __init__(self,
                 path: Path,
                 gens: List[Type]) -> None:
        Type.__init__(self)

        self.path = path
        self.generics = gens

    def children(self) -> typing.Iterable[Node]:
        return [self.path]


# --- pattern nodes ---

class PatternAny(Pattern):
    def children(self) -> typing.Iterable[Node]:
        return []


class PatternConst(Pattern):
    def __init__(self,
                 val: str,
                 tp: str) -> None:
        Pattern.__init__(self)

        self.value = val
        self.type = tp

    def _detail(self) -> typing.List[object]:
        return Pattern._detail(self) + [self.value]

    def children(self) -> typing.Iterable[Node]:
        return []


class PatternVar(Pattern):
    def __init__(self,
                 name: str) -> None:
        Pattern.__init__(self)

        self.name = name

    def _detail(self) -> typing.List[object]:
        return Pattern._detail(self) + [self.name]

    def children(self) -> typing.Iterable[Node]:
        return []


class PatternCall(Pattern):
    def __init__(self,
                 path: Path,
                 flds: List[Pattern]) -> None:
        Pattern.__init__(self)

        self.path = path
        self.fields = flds

    def children(self) -> typing.Iterable[Node]:
        return [self.path, self.fields]


# --- expr nodes ---

class Block(Expr, List[Expr]):
    def __init__(self, items: typing.List[Expr]) -> None:
        Expr.__init__(self)
        List[Expr].__init__(self, items)

        self.block: symbols.Block = None

    def children(self) -> typing.Iterable[Node]:
        return List.children(self)


class Let(Expr):
    def __init__(self,
                 name: str,
                 tp: Type,
                 val: Expr) -> None:
        Expr.__init__(self)

        self.name = name
        self.type = tp
        self.value = val

        self.symbol: symbols.Variable = None

    def _detail(self) -> typing.List[object]:
        return Expr._detail(self) + [self.symbol or self.name]

    def children(self) -> typing.Iterable[Node]:
        return [self.type, self.value]


class If(Expr):
    def __init__(self,
                 cond: Expr,
                 succ: Expr,
                 fail: Expr) -> None:
        Expr.__init__(self)

        self.condition = cond
        self.success = succ
        self.failure = fail

    def children(self) -> typing.Iterable[Node]:
        return [self.condition, self.success, self.failure]


class While(Expr):
    def __init__(self,
                 cond: Expr,
                 cont: Expr,
                 fail: Expr) -> None:
        Expr.__init__(self)

        self.condition = cond
        self.content = cont
        self.failure = fail

    def children(self) -> typing.Iterable[Node]:
        return [self.condition, self.content, self.failure]


class Match(Expr):
    def __init__(self,
                 expr: Expr,
                 arms: List[Arm]) -> None:
        Expr.__init__(self)

        self.expr = expr
        self.arms = arms

    def children(self) -> typing.Iterable[Node]:
        return [self.expr, self.arms]


class BinTest(Expr):
    def __init__(self,
                 left: Expr,
                 op: str,
                 right: Expr) -> None:
        Expr.__init__(self)

        self.left = left
        self.operator = op
        self.right = right

    def _detail(self) -> typing.List[object]:
        return Expr._detail(self) + [self.operator]

    def children(self) -> typing.Iterable[Node]:
        return [self.left, self.right]


class NotTest(Expr):
    def __init__(self,
                 expr: Expr) -> None:
        Expr.__init__(self)

        self.expr = expr

    def children(self) -> typing.Iterable[Node]:
        return [self.expr]


class Call(Expr):
    def __init__(self,
                 path: Path,
                 args: List[Expr]) -> None:
        Expr.__init__(self)

        self.path = path
        self.arguments = args

        self.match: types.Match = None

    def _detail(self) -> typing.List[object]:
        return Expr._detail(self) + [self.match]

    def children(self) -> typing.Iterable[Node]:
        return [self.path, self.arguments]


class Method(Expr):
    def __init__(self,
                 obj: Expr,
                 path: Path,
                 args: List[Expr]) -> None:
        Expr.__init__(self)

        self.object = obj
        self.path = path
        self.arguments = args

        self.match: types.Match = None

    def _detail(self) -> typing.List[object]:
        return super()._detail() + [self.match]

    def children(self) -> typing.Iterable[Node]:
        return [self.object, self.path, self.arguments]


class Op(Expr):
    def __init__(self,
                 op: str,
                 args: List[Expr]) -> None:
        Expr.__init__(self)

        self.operator = op
        self.arguments = args

        self.match: types.Match = None

    def _detail(self) -> typing.List[object]:
        return Expr._detail(self) + [self.match or self.operator]

    def children(self) -> typing.Iterable[Node]:
        return [self.arguments]


class Cast(Expr):
    def __init__(self,
                 expr: Expr,
                 tp: Type) -> None:
        Expr.__init__(self)

        self.expr = expr
        self.type = tp

        self.match: types.Match = None

    def _detail(self) -> typing.List[object]:
        return Expr._detail(self) + [self.match]

    def children(self) -> typing.Iterable[Node]:
        return [self.expr, self.type]


class Member(Expr):
    def __init__(self,
                 expr: Expr,
                 mem: Path) -> None:
        Expr.__init__(self)

        self.expr = expr
        self.member = mem

    def children(self) -> typing.Iterable[Node]:
        return [self.expr, self.member]


class Var(Expr):
    def __init__(self,
                 path: Path) -> None:
        Expr.__init__(self)

        self.path = path

        self.variable: typing.Union[symbols.Variable, symbols.Constant] = None

    def _detail(self) -> typing.List[object]:
        return Expr._detail(self) + [self.variable]

    def children(self) -> typing.Iterable[Node]:
        return [self.path]


class Const(Expr):
    def __init__(self,
                 val: str,
                 tp: str) -> None:
        Expr.__init__(self)

        self.value = val
        self.type = tp

    def _detail(self) -> typing.List[object]:
        return Expr._detail(self) + [self.value]

    def children(self) -> typing.Iterable[Node]:
        return []


class Assn(Expr):
    def __init__(self,
                 var: Expr,
                 val: Expr) -> None:
        Expr.__init__(self)

        self.variable = var
        self.value = val

    def children(self) -> typing.Iterable[Node]:
        return [self.variable, self.value]


class IncAssn(Expr):
    def __init__(self,
                 var: Expr,
                 op: str,
                 val: Expr) -> None:
        Expr.__init__(self)

        self.variable = var
        self.operator = op
        self.value = val

        self.match: types.Match = None

    def _detail(self) -> typing.List[object]:
        return Expr._detail(self) + [self.match or self.operator]

    def children(self) -> typing.Iterable[Node]:
        return [self.variable, self.value]


class Return(Expr):
    def __init__(self,
                 val: Expr) -> None:
        Expr.__init__(self)

        self.value = val

        self.target: Def = None

    def _detail(self) -> typing.List[object]:
        return super()._detail() + [self.target]

    def children(self) -> typing.Iterable[Node]:
        return [self.value]


class Break(Expr):
    def __init__(self,
                 val: Expr) -> None:
        Expr.__init__(self)

        self.value = val

        self.target: While = None

    def _detail(self) -> typing.List[object]:
        return super()._detail() + [self.target]

    def children(self) -> typing.Iterable[Node]:
        return [self.value]


class Continue(Expr):
    def __init__(self) -> None:
        Expr.__init__(self)

        self.target: While = None

    def _detail(self) -> typing.List[object]:
        return super()._detail() + [self.target]

    def children(self) -> typing.Iterable[Node]:
        return []


class Redo(Expr):
    def __init__(self) -> None:
        Expr.__init__(self)

        self.target: While = None

    def children(self) -> typing.Iterable[Node]:
        return []


class Noop(Expr):
    def children(self) -> typing.Iterable[Node]:
        return []


# --- analyzer nodes ---

class Deref(Expr):
    def __init__(self, expr: Expr) -> None:
        Expr.__init__(self)

        self.expr = expr

    def children(self) -> typing.Iterable[Node]:
        return [self.expr]


class Void(Expr):
    def __init__(self, expr: Expr) -> None:
        Expr.__init__(self)

        self.expr = expr

    def children(self) -> typing.Iterable[Node]:
        return [self.expr]
