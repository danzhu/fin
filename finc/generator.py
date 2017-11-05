from typing import Dict, List, Union, Any, Iterable, Iterator
from . import builtin
from . import symbols
from . import types
from . import ast


INT_OP_TABLE = {
    # 'pos': 'pos',
    # 'neg': 'neg',
    'less': 'icmp slt',
    'greater': 'icmp sgt',
    'lessEqual': 'icmp sle',
    'greaterEqual': 'icmp sge',
    'equal': 'icmp eq',
    'notEqual': 'icmp ne',
    'plus': 'add',
    'minus': 'sub',
    'multiplies': 'mul',
    'divides': 'sdiv',
    'modulus': 'srem',
}


FLOAT_OP_TABLE = {
    # 'pos': 'pos',
    # 'neg': 'neg',
    'less': 'fcmp olt',
    'greater': 'fcmp ogt',
    'lessEqual': 'fcmp ole',
    'greaterEqual': 'fcmp oge',
    'equal': 'fcmp oeq',
    'notEqual': 'fcmp one',
    'plus': 'fadd',
    'minus': 'fsub',
    'multiplies': 'fmul',
    'divides': 'fdiv',
    'modulus': 'frem',
}


class Arg:
    def __init__(self, tp: str, val: str) -> None:
        self.type = tp
        self.value = val

    def __str__(self) -> str:
        return f'{self.type} {self.value}'


class Writer(Iterable[str]):
    def __init__(self, parent: 'Writer' = None) -> None:
        self._instrs: List[str] = []
        self._temps: int = 0
        self._indent: int = 0 if parent is None else parent._indent

    def __iter__(self) -> Iterator[str]:
        return iter(self._instrs)

    def _write(self, instr: str) -> None:
        self._instrs.append('  ' * self._indent + instr)

    def temp(self) -> str:
        temp = f'%t{self._temps}'
        self._temps += 1
        return temp

    def indent(self) -> None:
        self._indent += 1

    def dedent(self) -> None:
        self._indent -= 1

    def exec(self, name: Union[str, List[str]], *args: object) -> None:
        def format_arg(arg: object) -> str:
            if isinstance(arg, list):
                return '[' + ', '.join(str(a) for a in arg) + ']'

            return str(arg)

        ins = name if isinstance(name, str) else ' '.join(name)

        if len(args) > 0:
            ags = ', '.join(format_arg(a) for a in args)
            self._write(f'{ins} {ags}')
        else:
            self._write(ins)

    def call(self, name: Union[str, List[str]], *args: object) -> str:
        tmp = self.temp()
        ins = [name] if isinstance(name, str) else name
        self.exec([tmp, '='] + ins, *args)
        return tmp

    def comment(self, val: object) -> None:
        self._write(f'; {val}')

    def label(self, label: str) -> None:
        self.space()
        # trim the leading '%'
        self._instrs.append(f'{label.value[1:]}:')

    def space(self) -> None:
        self._instrs.append('')

    def extend(self, writer: 'Writer') -> None:
        self._instrs.extend(writer._instrs)


class Generator:
    def __init__(self) -> None:
        self._root: ast.Node
        self._module: symbols.Module

    def generate(self,
                 root: ast.Node,
                 mod: symbols.Module,
                 debug: bool) -> Iterable[str]:
        self._root = root
        self._module = mod

        writer = Writer()
        for decl in root.children():
            if isinstance(decl, ast.Import):
                continue

            if isinstance(decl, (ast.Struct, ast.Enum)):
                # Type(decl.symbol, writer, debug)
                pass
            elif isinstance(decl, ast.Def):
                Function(decl, writer, debug)
            else:
                assert False, 'unknown decl type'

            writer.space()

        return writer


# class Type:
#     def __init__(self,
#                  sym: Union[symbols.Struct, symbols.Enumeration],
#                  writer: Writer) -> None:
#         self.types: Dict[str, types.Type] = {}

#         writer.indent()
#         self.writer = Writer(writer)
#         writer.dedent()
#         self._gen(sym)

#         end = gen.label('END_TYPE')

#         name = sym.basename()
#         gens = len(sym.generics)

#         writer.comment(str(sym))
#         writer.instr('type', quote(name), str(gens), end)

#         writer.indent()

#         writer.comment('types')
#         for gen_sym in sym.generics:
#             writer.instr('!sz', gen_sym.fullname())
#             writer.space()

#         for tp_name, tp in sorted(self.types.items()):
#             writer.instr('!sz', tp_name)
#             writer.type(tp)
#             writer.space()

#         writer.space()
#         writer.comment('fields')
#         writer.extend(self.writer)

#         writer.dedent()
#         writer.instr('type_ret')
#         writer.label(end)

#         writer.indent()
#         if isinstance(sym, symbols.Struct):
#             for field in sym.fields:
#                 writer.instr('member', quote(field.name))
#         elif isinstance(sym, symbols.Enumeration):
#             writer.instr('member', quote('_value'))

#             for var in sym.variants:
#                 for field in var.fields:
#                     writer.instr('member', quote(field.name))
#         else:
#             assert False

#         writer.dedent()
#         writer.space()

#     def _gen(self, sym: Union[symbols.Struct, symbols.Enumeration]) -> None:
#         if isinstance(sym, symbols.Struct):
#             for field in sym.fields:
#                 self.writer.instr('!off', field.name)
#                 self.writer.instr('local', self._type(field.type))
#                 self.writer.space()
#         elif isinstance(sym, symbols.Enumeration):
#             # _value field
#             self.writer.instr('!off', '_value')
#             self.writer.instr('local', self._type(builtin.INT))
#             self.writer.space()

#             reset_target: str = None
#             for var in sym.variants:
#                 if len(var.fields) == 0:
#                     continue

#                 if reset_target is None:
#                     reset_target = var.fields[0].name
#                 else:
#                     self.writer.instr('reset', reset_target)

#                 for field in var.fields:
#                     self.writer.instr('!off', field.name)
#                     self.writer.instr('local', self._type(field.type))
#                     self.writer.space()
#         else:
#             assert False

#     def _type(self, tp: types.Type) -> str:
#         name = type_name(tp)
#         if not isinstance(tp, types.Generic):
#             self.types.setdefault(name, tp)

#         return name


class Function:
    def __init__(self,
                 node: ast.Def,
                 writer: Writer,
                 debug: bool) -> None:
        self._debug = debug

        self._labels: Dict[str, int] = {}

        self._temps = 0
        self._context: Dict[ast.Node, Dict[str, Any]] = {}

        name = fn_name(node.symbol)
        ret = type_name(node.symbol.ret)
        params = ', '.join([ref_sym(p) for p in node.symbol.params])

        self.writer = Writer(writer)

        self.writer.comment(node)
        self.writer.exec('define', f'{ret} @{name}({params}) {{')
        self.writer.indent()

        for var in node.symbol.locals:
            # HACK: shouldn't use exec here
            self.writer.exec(f'{var_name(var)} = alloca', type_name(var.type))

        res = self._gen(node.body)
        if node.symbol.ret == builtin.VOID:
            self.writer.exec('ret', 'void')
        else:
            self.writer.exec('ret', res)

        self.writer.dedent()
        self.writer.exec(f'}}')
        self.writer.space()

        writer.extend(self.writer)

    def label(self, name: str) -> str:
        count = self._labels.get(name, 0)
        self._labels[name] = count + 1
        return Arg('label', f'%{name}_{count}')

    def _gen(self, node: ast.Expr) -> Arg:
        if self._debug:
            self.writer.comment(repr(node))
            self.writer.indent()

        val = self._expr(node)

        if self._debug:
            self.writer.dedent()

        if val is not None:
            tp = type_name(node.expr_type)
            return Arg(tp, val)

    # def _member(self, tp: types.Type, mem: str) -> str:
    #     tp = types.remove_ref(tp)
    #     tp_name = type_name(tp)
    #     return f'{tp_name}:{mem}'

    def _call(self, match: types.Match, args: Iterable[str]) -> str:
        fn = match.source
        assert isinstance(fn, symbols.Function)

        # non-builtin function
        # if fn.module().name != '':
        #     self.writer.instr('call', match_name(match))
        #     return

        # if fn.name == 'subscript':
        #     self.writer.instr('addr_off', type_name(match.generics[0]))
        #     return

        # if fn.name == 'cast':
        #     frm = native_type_name(fn.params[0].type)
        #     tar = native_type_name(fn.ret)
        #     self.writer.instr(f'cast_{frm}_{tar}')
        #     return

        tp = match.params[0].type
        if tp == builtin.INT:
            assert fn.name in INT_OP_TABLE, f'unknown operator {fn.name}'
            op = INT_OP_TABLE[fn.name]
        elif tp == builtin.FLOAT:
            assert fn.name in FLOAT_OP_TABLE, f'unknown operator {fn.name}'
            op = FLOAT_OP_TABLE[fn.name]

        return self.writer.call([op, type_name(tp)], *(a.value for a in args))

    # def _match(self, pat: pattern.Pattern, tp: types.Type, nxt: str) -> None:
    #     self.writer.comment(f'match {pat}')

    #     self.writer.indent()

    #     # TODO: duplicate logic, merge with analyzer implicit cast generation
    #     while tp != pat.type:
    #         assert isinstance(tp, types.Reference)
    #         tp = tp.type
    #         self.writer.instr('load', self._type(tp))

    #     if isinstance(pat, pattern.Variable):
    #         self.writer.instr('store_var',
    #                           var_name(pat.variable),
    #                           self._type(pat.type))

    #     elif isinstance(pat, pattern.Constant):
    #         if pat.type == builtin.INT:
    #             self.writer.instr('const_i', str(pat.value))
    #             self.writer.instr('eq_i')
    #         elif pat.type == builtin.FLOAT:
    #             self.writer.instr('const_f', str(pat.value))
    #             self.writer.instr('eq_f')
    #         else:
    #             assert False, f'unknown const pattern type {pat.type}'

    #         self.writer.instr('br_false', nxt)

    #     elif isinstance(pat, pattern.Struct):
    #         tmp = self._temp()

    #         self._push_local(tmp, pat.type)

    #         self.writer.instr('store_var', tmp, self._type(pat.type))

    #         if isinstance(pat.type, types.EnumerationType):
    #             assert isinstance(pat.source, symbols.Variant)

    #             self.writer.instr('addr_var', tmp)
    #             self.writer.instr('load_mem',
    #                               self._member(pat.type, '_value'),
    #                               self._type(builtin.INT))
    #             self.writer.instr('const_i', str(pat.source.value))
    #             self.writer.instr('eq_i')
    #             self.writer.instr('br_false', nxt)
    #             self.writer.space()
    #         else:
    #             assert isinstance(pat.type, types.StructType)

    #         for p, f in zip(pat.subpatterns, pat.fields):
    #             if not p.tested() and not p.bound():
    #                 continue

    #             self.writer.instr('addr_var', tmp)
    #             self.writer.instr('load_mem',
    #                               self._member(pat.type, f.name),
    #                               self._type(f.type))
    #             self._match(p, f.type, nxt)

    #         self._pop_local(tmp)

    #     else:
    #         assert False

    #     self.writer.dedent()

    def _expr(self, expr: ast.Expr) -> str:
        if isinstance(expr, ast.Block):
            for child in expr[:-1]:
                self._gen(child)
                self.writer.space()

            val = self._gen(expr[-1])
            if val is not None:
                return val.value

        elif isinstance(expr, ast.Let):
            assert isinstance(expr.symbol, symbols.Variable)

            if expr.value is not None:
                val = self._gen(expr.value)
                self.writer.exec('store', val, ref_sym(expr.symbol))

        elif isinstance(expr, ast.If):
            then = self.label('then')
            els = self.label('else')
            end = self.label('end_if')
            has_else = not isinstance(expr.failure, ast.Noop)

            cond = self._gen(expr.condition)
            self.writer.exec('br', cond, then, els if has_else else end)

            self.writer.label(then)
            succ = self._gen(expr.success)
            self.writer.exec('br', end)

            if has_else:
                self.writer.label(els)
                fail = self._gen(expr.failure)
                self.writer.exec('br', end)

            self.writer.label(end)

            if has_else and succ is not None:
                assert fail is not None
                return self.writer.call(['phi', type_name(expr.expr_type)],
                                        [succ.value, then.value],
                                        [fail.value, els.value])

        elif isinstance(expr, ast.While):
            whl = self.label('while')
            do = self.label('do')
            els = self.label('otherwise')
            end = self.label('end_while')
            has_else = not isinstance(expr.failure, ast.Noop)

            self._context[expr] = {
                'break': end,
                'continue': whl,
                'redo': do,
            }

            self.writer.exec('br', whl)

            self.writer.label(whl)
            cond = self._gen(expr.condition)
            self.writer.exec('br', cond, do, els if has_else else end)

            self.writer.label(do)
            self._gen(expr.content)
            self.writer.exec('br', whl)

            if has_else:
                self.writer.label(els)
                self._gen(expr.failure)
                self.writer.exec('br', end)

            self.writer.label(end)

            # FIXME: break returning values

        # elif isinstance(expr, ast.Match):
        #     end = self.label('END_MATCH')

        #     self._gen(expr.expr)

        #     for arm in expr.arms:
        #         nxt = self.gen.label('ARM')

        #         for var in arm.pat.variables():
        #             self._push_local(var_name(var.variable), var.variable.type)

        #         if arm.pat.tested() or arm.pat.bound():
        #             self.writer.instr('dup', self._type(expr.expr.expr_type))
        #             self._match(arm.pat, expr.expr.expr_type, nxt)

        #         self.writer.instr('pop', self._type(expr.expr.expr_type))

        #         self._gen(arm.content, stk)

        #         for var in arm.pat.variables():
        #             self._pop_local(var_name(var.variable))

        #         self.writer.instr('br', end)
        #         self.writer.label(nxt)

        #     # abort when no match found
        #     self.writer.instr('error')

        #     self.writer.label(end)

        # elif isinstance(expr, ast.BinTest):
        #     jump = self.gen.label('SHORT_CIRCUIT')
        #     end = self.gen.label('END_TEST')

        #     self._gen(expr.left, stk)

        #     if expr.operator == 'and':
        #         self.writer.instr('br_false', jump)
        #     elif expr.operator == 'or':
        #         self.writer.instr('br_true', jump)
        #     else:
        #         assert False, 'unknown binary test type'

        #     self._gen(expr.right, stk)
        #     self.writer.instr('br', end)
        #     self.writer.label(jump)

        #     if expr.operator == 'and':
        #         self.writer.instr('const_false')
        #     elif expr.operator == 'or':
        #         self.writer.instr('const_true')
        #     else:
        #         assert False, 'unknown binary test type'

        #     self.writer.label(end)

        # elif isinstance(expr, ast.NotTest):
        #     self._gen(expr.expr, stk)
        #     self.writer.instr('not')

        # elif isinstance(expr, ast.Call):
        #     sym = expr.match.source

        #     if isinstance(sym, symbols.Function):
        #         for child in expr.arguments:
        #             stk = self._gen(child, stk)

        #         self._call(expr.match)

        #     elif isinstance(sym, (symbols.Struct, symbols.Variant)):
        #         tmp = self._temp()

        #         tp = expr.match.ret
        #         self._push_local(tmp, tp)

        #         assert isinstance(tp, (types.StructType,
        #                                types.EnumerationType))

        #         if isinstance(sym, symbols.Variant):
        #             self.writer.instr('addr_var', tmp)
        #             # TODO: user-defined value type
        #             self.writer.instr('const_i', str(sym.value))
        #             self.writer.instr('store_mem',
        #                               self._member(tp, '_value'),
        #                               self._type(builtin.INT))

        #         # silence type checker
        #         assert isinstance(sym, (symbols.Struct, symbols.Variant))

        #         assert len(expr.arguments) == len(sym.fields)
        #         for child, field in zip(expr.arguments, sym.fields):
        #             self.writer.instr('addr_var', tmp)
        #             self._gen(child, stk)
        #             self.writer.instr('store_mem',
        #                               self._member(tp, field.name),
        #                               self._type(child.expr_type))

        #         self.writer.instr('load_var', tmp, self._type(tp))
        #         self._pop_local(tmp)

        #     else:
        #         assert False, 'unknown match source type'

        # elif isinstance(expr, ast.Method):
        #     stk = self._gen(expr.object, stk)

        #     for child in expr.arguments:
        #         stk = self._gen(child, stk)

        #     self._call(expr.match)

        elif isinstance(expr, ast.Op):
            args = [self._gen(child) for child in expr.arguments]

            return self._call(expr.match, args)

        elif isinstance(expr, ast.Cast):
            res = self._gen(expr.expr)
            return self._call(expr.match, res)

        # elif isinstance(expr, ast.Member):
        #     self._gen(expr.expr, stk)

        #     assert expr.member.path is None, 'member path not implemented'

        #     tp = expr.expr.expr_type
        #     mem = expr.member.name
        #     self.writer.instr('addr_mem', self._member(tp, mem))

        elif isinstance(expr, ast.Var):
            if isinstance(expr.variable, symbols.Constant):
                tp = expr.variable.type
                if not isinstance(tp, types.StructType):
                    raise NotImplementedError()

                if isinstance(expr.variable.value, bool):
                    return 'true' if expr.variable.value else 'false'
                else:
                    raise NotImplementedError()

            elif isinstance(expr.variable, symbols.Variable):
                return var_name(expr.variable)

            else:
                assert False, 'unknown var type'

        elif isinstance(expr, ast.Const):
            return expr.value

        elif isinstance(expr, ast.Assn):
            var = self._gen(expr.variable)
            val = self._gen(expr.value)

            self.writer.exec('store', val, var)

        # elif isinstance(expr, ast.IncAssn):
        #     # left
        #     stk = self._gen(expr.variable, stk)
        #     self.writer.instr('dup', self._type(expr.variable.expr_type))
        #     # FIXME: this only works for buitin operators
        #     self.writer.instr('load', self._type(expr.match.params[0].type))

        #     # right
        #     stk = self._gen(expr.value, stk)

        #     # call
        #     self._call(expr.match)

        #     # assn
        #     self.writer.instr('store', self._type(expr.match.ret))

        # elif isinstance(expr, ast.Return):
        #     stk = self._gen(expr.value, stk)

        #     cxt = self._context[expr.target]

        #     self._exit(stk, cxt['before'])

        #     # TODO: cleanup variables for RAII
        #     if expr.value.expr_type == builtin.VOID:
        #         self.writer.instr('end')
        #     else:
        #         self.writer.instr('ret', self._type(expr.value.expr_type))

        # elif isinstance(expr, ast.Break):
        #     stk = self._gen(expr.value, stk)
        #     cxt = self._context[expr.target]

        #     if expr.value.expr_type == builtin.VOID:
        #         self._exit(stk, cxt['after'])
        #     else:
        #         self._reduce(stk, cxt['after'])

        #     self.writer.instr('br', cxt['break'])

        # elif isinstance(expr, ast.Continue):
        #     cxt = self._context[expr.target]

        #     self._exit(stk, cxt['before'])
        #     self.writer.instr('br', cxt['continue'])

        # elif isinstance(expr, ast.Redo):
        #     cxt = self._context[expr.target]

        #     self._exit(stk, cxt['before'])
        #     self.writer.instr('br', cxt['redo'])

        elif isinstance(expr, ast.Noop):
            # well, it's noop
            return None

        elif isinstance(expr, ast.Deref):
            val = self._gen(expr.expr)
            return self.writer.call('load', type_name(expr.expr_type), val)

        # elif isinstance(expr, ast.Void):
        #     self.writer.instr('pop', self._type(expr.expr.expr_type))

        else:
            assert False, f'unknown expr type {expr}'


def type_name(tp: types.Type) -> str:
    if isinstance(tp, types.Array):
        return f'[{type_name(tp.type)}]'

    if isinstance(tp, types.Reference):
        return type_name(tp.type) + '*'

    if isinstance(tp, types.Generic):
        return tp.fullname()

    if isinstance(tp, (types.StructType, types.EnumerationType)):
        if tp == builtin.INT:
            return 'i32'

        if tp == builtin.FLOAT:
            return 'float'

        if tp == builtin.BOOL:
            return 'i1'

        # FIXME: user types
        # name = tp.symbol.fullname()

        # if len(tp.generics) > 0:
        #     name += '{' + \
        #         ','.join(type_name(g) for g in tp.generics) + \
        #         '}'

        # return name

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
    return f'%{var.name}_{tp}{var.index}'

def ref_sym(var: symbols.Variable) -> Arg:
    return Arg(type_name(var.var_type()), var_name(var))


def fn_name(fn: symbols.Function) -> str:
    return f'"{fn.basename()}"'


def native_type_name(tp: types.Type) -> str:
    return tp.fullname()[0].lower()
