from typing import Dict, Set, List, Union, Any, Sequence, Iterable, Iterator
from . import builtin
from . import symbols
from . import types
from . import pattern
from . import ast
from . import instr


OP_TABLE = {
    'pos': 'pos',
    'neg': 'neg',
    'less': 'lt',
    'greater': 'gt',
    'lessEqual': 'le',
    'greaterEqual': 'ge',
    'equal': 'eq',
    'notEqual': 'ne',
    'plus': 'add',
    'minus': 'sub',
    'multiplies': 'mult',
    'divides': 'div',
    'modulus': 'mod',
}


class Writer(Iterable[instr.Instr]):
    def __init__(self, parent: 'Writer' = None) -> None:
        self._instrs: List[instr.Instr] = []
        self._indent: int = 0 if parent is None else parent._indent

    def __iter__(self) -> Iterator[instr.Instr]:
        return iter(self._instrs)

    def _write(self, tokens: Sequence[str]) -> None:
        # TODO: line content
        ins = instr.Instr(tokens, self._indent)
        self._instrs.append(ins)

    def indent(self) -> None:
        self._indent += 1

    def dedent(self) -> None:
        self._indent -= 1

    def instr(self, *args: str) -> None:
        self._write(args)

    def comment(self, val: object) -> None:
        self._write([f'# {val}'])

    def label(self, label: str) -> None:
        self._write([f'{label}:'])

    def space(self) -> None:
        self._write([])

    def extend(self, writer: 'Writer') -> None:
        self._instrs.extend(writer._instrs)

    def type(self, tp: types.Type) -> None:
        if isinstance(tp, types.Reference):
            self.instr('size_p')

        elif isinstance(tp, types.Array):
            assert tp.length is not None

            self.type(tp.type)
            self.instr('size_arr', str(tp.length))

        elif isinstance(tp, types.Generic):
            self.instr('size_dup', str(tp.symbol.index))

        elif isinstance(tp, types.Special):
            assert False, 'when?'

        elif isinstance(tp, (types.StructType, types.EnumerationType)):
            if tp == builtin.BOOL:
                self.instr('size_b')
            elif tp == builtin.INT:
                self.instr('size_i')
            elif tp == builtin.FLOAT:
                self.instr('size_f')
            else:
                for gen in tp.generics:
                    self.type(gen)

                self.instr('type_call', tp.symbol.fullname())

        else:
            assert False, f'unknown type {tp}'

    def contract(self, ctr: types.Match) -> None:
        assert isinstance(ctr.source, symbols.Function)

        for gen in ctr.generics:
            self.type(gen)

        self.instr('contract', ctr.source.fullname())


class TypeList:
    def __init__(self,
                 val: 'types.Type' = None,
                 parent: 'TypeList' = None) -> None:
        self.value = val
        self.parent = parent

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TypeList):
            return False

        if self is other:
            return True

        if self.value != other.value:
            return False

        return self.parent == other.parent

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def push(self, val: types.Type) -> 'TypeList':
        assert val is not None
        return TypeList(val, self)

    def pop(self) -> 'TypeList':
        assert self.parent is not None
        return self.parent


class TypeTree:
    def __init__(self,
                 name: str = None,
                 tp: 'types.Type' = None,
                 par: 'TypeTree' = None) -> None:
        self.name = name
        self.type = tp
        self.parent = par
        self.children: List[TypeTree] = []

    def push(self, name: str, tp: types.Type) -> 'TypeTree':
        assert name is not None
        assert tp is not None

        node = TypeTree(name, tp, self)
        self.children.append(node)
        return node

    def pop(self) -> 'TypeTree':
        return self.parent


class SymbolRef:
    def __init__(self,
                 sym: Union[symbols.Struct, symbols.Enumeration]) -> None:
        self.symbol = sym
        self.member_refs: Set[str] = set()

    def ref_member(self, mem: str) -> None:
        self.member_refs.add(mem)


class TypeRef:
    def __init__(self, tp: types.Type) -> None:
        self.type = tp
        self.member_refs: Set[str] = set()

    def ref_member(self, mem: str) -> None:
        self.member_refs.add(mem)


class Generator:
    def __init__(self) -> None:
        self._root: ast.Node
        self._module: symbols.Module

        self._labels: Dict[str, int] = None
        self._function_refs: Set[symbols.Function] = None
        self._type_refs: Dict[str, SymbolRef] = None

    def generate(self,
                 root: ast.Node,
                 mod: symbols.Module) -> Iterable[instr.Instr]:
        self._root = root
        self._module = mod

        self._labels = {}
        self._function_refs = set()
        self._type_refs = {}

        body = Writer()
        for decl in root.children():
            if isinstance(decl, ast.Import):
                continue

            if isinstance(decl, (ast.Struct, ast.Enum)):
                Type(self, decl.symbol, body)
            elif isinstance(decl, ast.Def):
                Function(self, decl, body)
            else:
                assert False, 'unknown decl type'

            body.space()

        writer = Writer()
        writer.instr('lib', quote(mod.name))
        writer.space()

        ref_mod = None
        for fn in sorted(self._function_refs):
            module = fn.module()

            if ref_mod != module:
                writer.instr('ref_lib', quote(module.fullname()))
                ref_mod = module

            writer.instr('ref_fn', quote(fn.basename()))

        # FIXME: type need to be in its module
        # writer.space()
        # for tp_name, tp in self._type_refs.items():
        #     writer.instr('ref_type', tp.symbol.fullname())
        #     for mem in tp.member_refs:
        #         writer.instr('ref_mem', quote(mem))

        writer.space()
        writer.extend(body)

        return writer

    def label(self, name: str) -> str:
        count = self._labels.get(name, 0)
        self._labels[name] = count + 1
        return f'{name}_{count}'

    def ref_function(self, fn: symbols.Function) -> None:
        mod = fn.module()

        # don't ref current module / builtin
        if mod != self._module:
            self._function_refs.add(fn)

    def ref_member(self, tp: types.Type, mem: str) -> None:
        assert isinstance(tp, (types.StructType, types.EnumerationType))

        sym = tp.symbol
        mod = sym.module()
        if mod == self._module:
            return

        name = sym.fullname()
        if name in self._type_refs:
            ref = self._type_refs[name]
        else:
            ref = SymbolRef(sym)
            self._type_refs[name] = ref

        ref.ref_member(mem)


class Type:
    def __init__(self,
                 gen: Generator,
                 sym: Union[symbols.Struct, symbols.Enumeration],
                 writer: Writer) -> None:
        self.types: Dict[str, types.Type] = {}

        writer.indent()
        self.writer = Writer(writer)
        writer.dedent()
        self._gen(sym)

        end = gen.label('END_TYPE')

        name = sym.basename()
        gens = len(sym.generics)

        writer.comment(str(sym))
        writer.instr('type', quote(name), str(gens), end)

        writer.indent()

        writer.comment('types')
        for gen_sym in sym.generics:
            writer.instr('!sz', gen_sym.fullname())
            writer.space()

        for tp_name, tp in sorted(self.types.items()):
            writer.instr('!sz', tp_name)
            writer.type(tp)
            writer.space()

        writer.space()
        writer.comment('fields')
        writer.extend(self.writer)

        writer.dedent()
        writer.instr('type_ret')
        writer.label(end)

        writer.indent()
        if isinstance(sym, symbols.Struct):
            for field in sym.fields:
                writer.instr('member', quote(field.name))
        elif isinstance(sym, symbols.Enumeration):
            writer.instr('member', quote('_value'))

            for var in sym.variants:
                for field in var.fields:
                    writer.instr('member', quote(field.name))
        else:
            assert False

        writer.dedent()
        writer.space()

    def _gen(self, sym: Union[symbols.Struct, symbols.Enumeration]) -> None:
        if isinstance(sym, symbols.Struct):
            for field in sym.fields:
                self.writer.instr('!off', field.name)
                self.writer.instr('local', self._type(field.type))
                self.writer.space()
        elif isinstance(sym, symbols.Enumeration):
            # _value field
            self.writer.instr('!off', '_value')
            self.writer.instr('local', self._type(builtin.INT))
            self.writer.space()

            reset_target: str = None
            for var in sym.variants:
                if len(var.fields) == 0:
                    continue

                if reset_target is None:
                    reset_target = var.fields[0].name
                else:
                    self.writer.instr('reset', reset_target)

                for field in var.fields:
                    self.writer.instr('!off', field.name)
                    self.writer.instr('local', self._type(field.type))
                    self.writer.space()
        else:
            assert False

    def _type(self, tp: types.Type) -> str:
        name = type_name(tp)
        if not isinstance(tp, types.Generic):
            self.types.setdefault(name, tp)

        return name


class Function:
    def __init__(self,
                 gen: Generator,
                 node: ast.Def,
                 writer: Writer) -> None:
        self.gen = gen

        self._temps = 0
        self._context: Dict[ast.Node, Dict[str, Any]] = {}
        self.types: Dict[str, TypeRef] = {}
        self.contracts: Dict[str, types.Match] = {}
        self.locals = TypeTree()

        for param in node.symbol.params:
            self._type(param.type)

        stk = TypeList()
        self._context[node] = {'after': stk.push(node.symbol.ret)}

        self.writer = Writer(writer)
        self._gen(node.body, stk)
        if node.symbol.ret == builtin.VOID:
            self.writer.instr('end')
        else:
            self.writer.instr('ret', self._type(node.symbol.ret))

        name = node.symbol.basename()
        gens = len(node.symbol.generics)
        ctrs = 0  # TODO: contract bounds

        begin = self.gen.label('BEGIN_FN')
        end = self.gen.label('END_FN')

        writer.comment(node)
        writer.instr('fn', quote(name), str(gens), str(ctrs), begin, end)

        writer.indent()

        writer.comment('types')
        for gen_sym in node.symbol.generics:
            writer.instr('!sz', gen_sym.fullname())
            writer.space()

        for tp_name, tp in sorted(self.types.items()):
            writer.instr('!sz', tp_name)
            writer.type(tp.type)
            writer.space()

            if len(tp.member_refs) == 0:
                continue

            assert isinstance(tp.type, (types.StructType,
                                        types.EnumerationType))
            name = tp.type.symbol.fullname()

            # member refs
            writer.indent()
            for mem in tp.member_refs:
                writer.instr('!off', f'{tp_name}:{mem}')
                writer.instr('type_mem', f'{name}:{mem}')
                writer.space()

            writer.dedent()

        writer.space()
        writer.comment('contracts')
        for ctr_name, ctr in sorted(self.contracts.items()):
            # TODO: contract params

            writer.instr('!ctr', ctr_name)
            writer.contract(ctr)
            writer.space()

        writer.space()
        writer.comment('params')
        for param in node.symbol.params:
            writer.instr('!off', var_name(param))
            writer.instr('param', type_name(param.type))
            writer.space()

        writer.space()
        writer.comment('locals')
        assert self.locals.name is None, 'not all locals are popped'
        self._write_local(writer, self.locals)

        writer.dedent()
        writer.instr('sign')

        writer.label(begin)
        writer.extend(self.writer)

        writer.label(end)
        writer.space()

    def _write_local(self, writer: Writer, loc: TypeTree) -> None:
        reset_target: str = None
        for child in loc.children:
            if reset_target is None:
                reset_target = child.name
            else:
                writer.instr('reset', reset_target)

            writer.instr('!off', child.name)
            writer.instr('local', type_name(child.type))
            writer.space()

            self._write_local(writer, child)

    def _temp(self) -> str:
        temp = f't{self._temps}'
        self._temps += 1
        return temp

    def _gen(self, node: ast.Expr, stk: TypeList) -> TypeList:
        self.writer.comment(repr(node))

        self.writer.indent()

        self._expr(node, stk)
        if node.expr_type != builtin.VOID and \
                node.expr_type != builtin.DIVERGE:
            stk = stk.push(node.expr_type)

        self.writer.dedent()

        return stk

    def _type(self, tp: types.Type) -> str:
        name = type_name(tp)
        if name not in self.types and not isinstance(tp, types.Generic):
            self.types[name] = TypeRef(tp)

        return name

    def _contract(self, match: types.Match) -> str:
        assert isinstance(match.source, symbols.Function)
        self.gen.ref_function(match.source)

        name = match_name(match)
        self.contracts.setdefault(name, match)

        return name

    def _member(self, tp: types.Type, mem: str) -> str:
        tp = types.remove_ref(tp)
        tp_name = self._type(tp)
        name = f'{tp_name}:{mem}'
        self.types[tp_name].ref_member(mem)
        self.gen.ref_member(tp, mem)
        return name

    def _push_local(self, name: str, tp: types.Type) -> None:
        # TODO: assert
        # assert name not in self.locals

        self._type(tp)
        self.locals = self.locals.push(name, tp)

    def _pop_local(self, name: str) -> None:
        self.locals = self.locals.pop()

    def _exit(self, stk: TypeList, tar: TypeList) -> None:
        while stk != tar:
            # TODO: RAII cleanup for local variables
            self.writer.instr('pop', self._type(stk.value))
            stk = stk.pop()

    def _reduce(self, stk: TypeList, tar: TypeList) -> None:
        # no need for popping when stack is same
        if stk == tar:
            return

        tmp = self._temp()
        self._push_local(tmp, stk.value)
        self.writer.instr('store_var', tmp, self._type(stk.value))

        self._exit(stk.pop(), tar.pop())

        self.writer.instr('load_var', tmp, self._type(stk.value))
        self._pop_local(tmp)

    def _call(self, match: types.Match) -> None:
        fn = match.source
        assert isinstance(fn, symbols.Function)

        # non-builtin function
        if fn.module().name != '':
            self.writer.instr('call', self._contract(match))
            return

        if fn.name == 'subscript':
            self.writer.instr('addr_off', self._type(match.generics[0]))
            return

        if fn.name == 'cast':
            frm = native_type_name(fn.params[0].type)
            tar = native_type_name(fn.ret)
            self.writer.instr(f'cast_{frm}_{tar}')
            return

        assert fn.name in OP_TABLE, f'unknown operator {fn.name}'

        op = OP_TABLE[fn.name]
        name = native_type_name(fn.params[0].type)
        self.writer.instr(f'{op}_{name}')

    def _match(self, pat: pattern.Pattern, tp: types.Type, nxt: str) -> None:
        self.writer.comment(f'match {pat}')

        self.writer.indent()

        # TODO: duplicate logic, merge with analyzer implicit cast generation
        while tp != pat.type:
            assert isinstance(tp, types.Reference)
            tp = tp.type
            self.writer.instr('load', self._type(tp))

        if isinstance(pat, pattern.Variable):
            self.writer.instr('store_var',
                              var_name(pat.variable),
                              self._type(pat.type))

        elif isinstance(pat, pattern.Constant):
            if pat.type == builtin.INT:
                self.writer.instr('const_i', str(pat.value))
                self.writer.instr('eq_i')
            elif pat.type == builtin.FLOAT:
                self.writer.instr('const_f', str(pat.value))
                self.writer.instr('eq_f')
            else:
                assert False, f'unknown const pattern type {pat.type}'

            self.writer.instr('br_false', nxt)

        elif isinstance(pat, pattern.Struct):
            tmp = self._temp()

            self._push_local(tmp, pat.type)

            self.writer.instr('store_var', tmp, self._type(pat.type))

            if isinstance(pat.type, types.EnumerationType):
                assert isinstance(pat.source, symbols.Variant)

                self.writer.instr('addr_var', tmp)
                self.writer.instr('load_mem',
                                  self._member(pat.type, '_value'),
                                  self._type(builtin.INT))
                self.writer.instr('const_i', str(pat.source.value))
                self.writer.instr('eq_i')
                self.writer.instr('br_false', nxt)
                self.writer.space()
            else:
                assert isinstance(pat.type, types.StructType)

            for p, f in zip(pat.subpatterns, pat.fields):
                if not p.tested() and not p.bound():
                    continue

                self.writer.instr('addr_var', tmp)
                self.writer.instr('load_mem',
                                  self._member(pat.type, f.name),
                                  self._type(f.type))
                self._match(p, f.type, nxt)

            self._pop_local(tmp)

        else:
            assert False

        self.writer.dedent()

    def _expr(self, expr: ast.Expr, stk: TypeList) -> None:
        if isinstance(expr, ast.Block):
            for child in expr:
                stk = self._gen(child, stk)
                self.writer.space()

            for loc in expr.block.locals:
                self._pop_local(var_name(loc))

        elif isinstance(expr, ast.Let):
            assert isinstance(expr.symbol, symbols.Variable)

            self._push_local(var_name(expr.symbol), expr.symbol.type)
            if expr.value is not None:
                self._gen(expr.value, stk)
                self.writer.instr('store_var',
                                  var_name(expr.symbol),
                                  self._type(expr.symbol.type))

        elif isinstance(expr, ast.If):
            els = self.gen.label('ELSE')
            end = self.gen.label('END_IF')
            has_else = not isinstance(expr.failure, ast.Noop)

            self._gen(expr.condition, stk)
            self.writer.instr('br_false', els if has_else else end)
            self._gen(expr.success, stk)

            if has_else:
                self.writer.instr('br', end)
                self.writer.label(els)
                self._gen(expr.failure, stk)

            self.writer.label(end)

        elif isinstance(expr, ast.While):
            start = self.gen.label('WHILE')
            cond = self.gen.label('COND')
            end = self.gen.label('END_WHILE')

            self._context[expr] = {
                'break': end,
                'continue': cond,
                'redo': start,
                'before': stk,
                'after': stk.push(expr.expr_type)
            }

            self.writer.instr('br', cond)

            self.writer.label(start)
            self._gen(expr.content, stk)

            self.writer.label(cond)
            self._gen(expr.condition, stk)
            self.writer.instr('br_true', start)

            self._gen(expr.failure, stk)
            self.writer.label(end)

        elif isinstance(expr, ast.Match):
            end = self.gen.label('END_MATCH')

            self._gen(expr.expr, stk)

            for arm in expr.arms:
                nxt = self.gen.label('ARM')

                for var in arm.pat.variables():
                    self._push_local(var_name(var.variable), var.variable.type)

                if arm.pat.tested() or arm.pat.bound():
                    self.writer.instr('dup', self._type(expr.expr.expr_type))
                    self._match(arm.pat, expr.expr.expr_type, nxt)

                self.writer.instr('pop', self._type(expr.expr.expr_type))

                self._gen(arm.content, stk)

                for var in arm.pat.variables():
                    self._pop_local(var_name(var.variable))

                self.writer.instr('br', end)
                self.writer.label(nxt)

            # abort when no match found
            self.writer.instr('error')

            self.writer.label(end)

        elif isinstance(expr, ast.BinTest):
            jump = self.gen.label('SHORT_CIRCUIT')
            end = self.gen.label('END_TEST')

            self._gen(expr.left, stk)

            if expr.operator == 'and':
                self.writer.instr('br_false', jump)
            elif expr.operator == 'or':
                self.writer.instr('br_true', jump)
            else:
                assert False, 'unknown binary test type'

            self._gen(expr.right, stk)
            self.writer.instr('br', end)
            self.writer.label(jump)

            if expr.operator == 'and':
                self.writer.instr('const_false')
            elif expr.operator == 'or':
                self.writer.instr('const_true')
            else:
                assert False, 'unknown binary test type'

            self.writer.label(end)

        elif isinstance(expr, ast.NotTest):
            self._gen(expr.expr, stk)
            self.writer.instr('not')

        elif isinstance(expr, ast.Call):
            sym = expr.match.source

            if isinstance(sym, symbols.Function):
                for child in expr.arguments:
                    stk = self._gen(child, stk)

                self._call(expr.match)

            elif isinstance(sym, (symbols.Struct, symbols.Variant)):
                tmp = self._temp()

                tp = expr.match.ret
                self._push_local(tmp, tp)

                assert isinstance(tp, (types.StructType,
                                       types.EnumerationType))

                if isinstance(sym, symbols.Variant):
                    self.writer.instr('addr_var', tmp)
                    # TODO: user-defined value type
                    self.writer.instr('const_i', str(sym.value))
                    self.writer.instr('store_mem',
                                      self._member(tp, '_value'),
                                      self._type(builtin.INT))

                # silence type checker
                assert isinstance(sym, (symbols.Struct, symbols.Variant))

                assert len(expr.arguments) == len(sym.fields)
                for child, field in zip(expr.arguments, sym.fields):
                    self.writer.instr('addr_var', tmp)
                    self._gen(child, stk)
                    self.writer.instr('store_mem',
                                      self._member(tp, field.name),
                                      self._type(child.expr_type))

                self.writer.instr('load_var', tmp, self._type(tp))
                self._pop_local(tmp)

            else:
                assert False, 'unknown match source type'

        elif isinstance(expr, ast.Method):
            stk = self._gen(expr.object, stk)

            for child in expr.arguments:
                stk = self._gen(child, stk)

            self._call(expr.match)

        elif isinstance(expr, ast.Op):
            for child in expr.arguments:
                stk = self._gen(child, stk)

            self._call(expr.match)

        elif isinstance(expr, ast.Cast):
            self._gen(expr.expr, stk)
            self._call(expr.match)

        elif isinstance(expr, ast.Member):
            self._gen(expr.expr, stk)

            assert expr.member.path is None, 'member path not implemented'

            tp = expr.expr.expr_type
            mem = expr.member.name
            self.writer.instr('addr_mem', self._member(tp, mem))

        elif isinstance(expr, ast.Var):
            if isinstance(expr.variable, symbols.Constant):
                tp = expr.variable.type
                if not isinstance(tp, types.StructType):
                    raise NotImplementedError()

                if isinstance(expr.variable.value, bool):
                    if expr.variable.value:
                        self.writer.instr('const_true')
                    else:
                        self.writer.instr('const_false')
                else:
                    raise NotImplementedError()

            elif isinstance(expr.variable, symbols.Variable):
                if expr.variable.is_arg:
                    self.writer.instr('addr_arg', var_name(expr.variable))
                else:
                    self.writer.instr('addr_var', var_name(expr.variable))

            else:
                assert False, 'unknown var type'

        elif isinstance(expr, ast.Const):
            if expr.type == 'num':
                self.writer.instr('const_i', expr.value)
            elif expr.type == 'float':
                self.writer.instr('const_f', expr.value)
            else:
                assert False, 'unknown const type'

        elif isinstance(expr, ast.Assn):
            stk = self._gen(expr.variable, stk)
            stk = self._gen(expr.value, stk)

            self.writer.instr('store', self._type(expr.value.expr_type))

        elif isinstance(expr, ast.IncAssn):
            # left
            stk = self._gen(expr.variable, stk)
            self.writer.instr('dup', self._type(expr.variable.expr_type))
            # FIXME: this only works for buitin operators
            self.writer.instr('load', self._type(expr.match.params[0].type))

            # right
            stk = self._gen(expr.value, stk)

            # call
            self._call(expr.match)

            # assn
            self.writer.instr('store', self._type(expr.match.ret))

        elif isinstance(expr, ast.Return):
            stk = self._gen(expr.value, stk)

            cxt = self._context[expr.target]

            self._exit(stk, cxt['before'])

            # TODO: cleanup variables for RAII
            if expr.value.expr_type == builtin.VOID:
                self.writer.instr('end')
            else:
                self.writer.instr('ret', self._type(expr.value.expr_type))

        elif isinstance(expr, ast.Break):
            stk = self._gen(expr.value, stk)
            cxt = self._context[expr.target]

            if expr.value.expr_type == builtin.VOID:
                self._exit(stk, cxt['after'])
            else:
                self._reduce(stk, cxt['after'])

            self.writer.instr('br', cxt['break'])

        elif isinstance(expr, ast.Continue):
            cxt = self._context[expr.target]

            self._exit(stk, cxt['before'])
            self.writer.instr('br', cxt['continue'])

        elif isinstance(expr, ast.Redo):
            cxt = self._context[expr.target]

            self._exit(stk, cxt['before'])
            self.writer.instr('br', cxt['redo'])

        elif isinstance(expr, ast.Noop):
            # well, it's noop
            pass

        elif isinstance(expr, ast.Deref):
            self._gen(expr.expr, stk)
            self.writer.instr('load', self._type(expr.expr_type))

        elif isinstance(expr, ast.Void):
            self.writer.instr('pop', self._type(expr.expr.expr_type))

        else:
            assert False, f'unknown expr type {expr}'


def type_name(tp: types.Type) -> str:
    if isinstance(tp, types.Array):
        return f'[{type_name(tp.type)}]'

    if isinstance(tp, types.Reference):
        return '&'

    if isinstance(tp, types.Generic):
        return tp.fullname()

    if isinstance(tp, (types.StructType, types.EnumerationType)):
        name = tp.symbol.fullname()

        if len(tp.generics) > 0:
            name += '{' + \
                ','.join(type_name(g) for g in tp.generics) + \
                '}'

        return name

    assert False, tp


def match_name(match: types.Match) -> str:
    fn = match.source
    assert isinstance(fn, symbols.Function)

    name = fn.fullname()
    if len(fn.generics) > 0:
        name += '`' + ','.join(type_name(g) for g in match.generics)

    # TODO: constraints

    return name


def var_name(var: symbols.Variable) -> str:
    tp = 'p' if var.is_arg else 'l'
    return f'{var.name}_{tp}{var.index}'


def quote(s: str) -> str:
    return f"'{s}'"


def native_type_name(tp: types.Type) -> str:
    return tp.fullname()[0].lower()
