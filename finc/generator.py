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
        if self.value is None:
            return self.type

        return f'{self.type} {self.value}'


class Writer(Iterable[str]):
    def __init__(self, parent: 'Writer' = None) -> None:
        self._instrs: List[str] = []
        self._temps: int = 0
        self._indent: int = 0 if parent is None else parent._indent
        self._label: Arg = None

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

    def exec(self, instrs: object, *args: object) -> None:
        def format_arg(arg: object) -> str:
            if isinstance(arg, tuple):
                return '(' + ', '.join(str(a) for a in arg) + ')'

            if isinstance(arg, list):
                return '[ ' + ', '.join(str(a) for a in arg) + ' ]'

            return str(arg)

        ins = ' '.join(format_arg(i) for i in instrs) \
            if isinstance(instrs, list) \
            else format_arg(instrs)

        if len(args) > 0:
            ags = ', '.join(format_arg(a) for a in args)
            self._write(f'{ins} {ags}')
        else:
            self._write(ins)

    def call(self, instrs: object, *args: object) -> str:
        tmp = self.temp()
        ins = instrs if isinstance(instrs, list) else [instrs]
        self.exec([tmp, '='] + ins, *args)
        return tmp

    def begin(self, instrs: object) -> None:
        ins = instrs if isinstance(instrs, list) else [instrs]
        self.exec(ins + ['{'])

        self._temps = 0
        self._label = None

    def end(self) -> None:
        self.exec('}')

    def comment(self, val: object) -> None:
        self._write(f'; {val}')

    def label(self, label: Arg) -> None:
        if self._label is not None:
            self.space()

        # trim the leading '%'
        lab = label.value[1:]
        self._instrs.append(f'{lab}:')

        self._label = label

    def space(self) -> None:
        self._instrs.append('')

    def block(self) -> Arg:
        assert self._label is not None
        return self._label

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
        params = tuple(Arg(type_name(p.type), param_name(p))
                       for p in node.symbol.params)

        self.writer = writer

        self.writer.begin(['define', ret, name, params])
        self.writer.indent()

        entry = self.label('entry')
        self.writer.label(entry)

        for p, param in zip(params, node.symbol.params):
            self.writer.exec([var_name(param), '=', 'alloca'],
                             type_name(param.type))
            self.writer.exec('store', p, ref_sym(param))

        for var in node.symbol.locals:
            # HACK: shouldn't use exec here
            self.writer.exec([var_name(var), '=', 'alloca'],
                             type_name(var.type))

        res = self._gen(node.body)
        self.writer.exec('ret', res)

        self.writer.dedent()
        self.writer.end()
        self.writer.space()

    def label(self, name: str) -> Arg:
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

        tp = type_name(node.expr_type)
        return Arg(tp, val)

    # def _member(self, tp: types.Type, mem: str) -> str:
    #     tp = types.remove_ref(tp)
    #     tp_name = type_name(tp)
    #     return f'{tp_name}:{mem}'

    def _call(self, match: types.Match, args: Iterable[Arg]) -> str:
        fn = match.source
        assert isinstance(fn, symbols.Function)

        # non-builtin function
        if fn.module().name != '':
            return self.writer.call(['call',
                                     type_name(match.ret),
                                     match_name(match)],
                                    tuple(args))

        # if fn.name == 'subscript':
        #     self.writer.instr('addr_off', type_name(match.generics[0]))
        #     return

        # if fn.name == 'cast':
        #     frm = native_type_name(fn.params[0].type)
        #     tar = native_type_name(fn.ret)
        #     self.writer.instr(f'cast_{frm}_{tar}')
        #     return

        # binary operator
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

            return self._gen(expr[-1]).value

        if isinstance(expr, ast.Let):
            assert isinstance(expr.symbol, symbols.Variable)

            if expr.value is not None:
                val = self._gen(expr.value)
                self.writer.exec('store', val, ref_sym(expr.symbol))

            return None

        if isinstance(expr, ast.If):
            then = self.label('then')
            els = self.label('else')
            end = self.label('end_if')
            has_else = not isinstance(expr.failure, ast.Noop)

            cond = self._gen(expr.condition)
            self.writer.exec('br', cond, then, els if has_else else end)

            self.writer.label(then)
            succ = self._gen(expr.success)
            then = self.writer.block()
            self.writer.exec('br', end)

            if has_else:
                self.writer.label(els)
                fail = self._gen(expr.failure)
                els = self.writer.block()
                self.writer.exec('br', end)

            self.writer.label(end)

            if has_else and succ is not None:
                assert fail is not None
                return self.writer.call(['phi', type_name(expr.expr_type)],
                                        [succ.value, then.value],
                                        [fail.value, els.value])

            return None

        if isinstance(expr, ast.While):
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
            return None

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

        if isinstance(expr, ast.BinTest):
            nxt = self.label('next')
            end = self.label('end_test')

            beg = self.writer.block()
            left = self._gen(expr.left)

            if expr.operator == 'and':
                self.writer.exec('br', left, nxt, end)
            elif expr.operator == 'or':
                self.writer.exec('br', left, end, nxt)
            else:
                assert False, 'unknown binary test type'

            self.writer.label(nxt)
            right = self._gen(expr.right)
            self.writer.exec('br', end)

            self.writer.label(end)
            return self.writer.call(['phi', type_name(expr.expr_type)],
                                    [left.value, beg.value],
                                    [right.value, nxt.value])

        if isinstance(expr, ast.NotTest):
            val = self._gen(expr.expr)
            return self.writer.call('xor', val, 'true')

        if isinstance(expr, ast.Call):
            sym = expr.match.source

            if isinstance(sym, symbols.Function):
                args = [self._gen(a) for a in expr.arguments]

                return self._call(expr.match, args)

            # elif isinstance(sym, (symbols.Struct, symbols.Variant)):
            #     tmp = self._temp()

            #     tp = expr.match.ret
            #     self._push_local(tmp, tp)

            #     assert isinstance(tp, (types.StructType,
            #                            types.EnumerationType))

            #     if isinstance(sym, symbols.Variant):
            #         self.writer.instr('addr_var', tmp)
            #         # TODO: user-defined value type
            #         self.writer.instr('const_i', str(sym.value))
            #         self.writer.instr('store_mem',
            #                           self._member(tp, '_value'),
            #                           self._type(builtin.INT))

            #     # silence type checker
            #     assert isinstance(sym, (symbols.Struct, symbols.Variant))

            #     assert len(expr.arguments) == len(sym.fields)
            #     for child, field in zip(expr.arguments, sym.fields):
            #         self.writer.instr('addr_var', tmp)
            #         self._gen(child, stk)
            #         self.writer.instr('store_mem',
            #                           self._member(tp, field.name),
            #                           self._type(child.expr_type))

            #     self.writer.instr('load_var', tmp, self._type(tp))
            #     self._pop_local(tmp)

            else:
                assert False, 'unknown match source type'

        # elif isinstance(expr, ast.Method):
        #     stk = self._gen(expr.object, stk)

        #     for child in expr.arguments:
        #         stk = self._gen(child, stk)

        #     self._call(expr.match)

        if isinstance(expr, ast.Op):
            args = [self._gen(child) for child in expr.arguments]
            return self._call(expr.match, args)

        if isinstance(expr, ast.Cast):
            res = self._gen(expr.expr)
            return self._call(expr.match, [res])

        # elif isinstance(expr, ast.Member):
        #     self._gen(expr.expr, stk)

        #     assert expr.member.path is None, 'member path not implemented'

        #     tp = expr.expr.expr_type
        #     mem = expr.member.name
        #     self.writer.instr('addr_mem', self._member(tp, mem))

        if isinstance(expr, ast.Var):
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

        if isinstance(expr, ast.Const):
            return expr.value

        if isinstance(expr, ast.Assn):
            var = self._gen(expr.variable)
            val = self._gen(expr.value)

            self.writer.exec('store', val, var)
            return None

        if isinstance(expr, ast.IncAssn):
            var = self._gen(expr.variable)
            tp = expr.match.params[0].type
            # FIXME: this only works for buitin operators,
            # require conversion sequence for right arg
            load = self.writer.call('load', type_name(tp), var)

            val = self._gen(expr.value)

            ret = self._call(expr.match, [Arg(type_name(tp), load), val])

            self.writer.exec('store', Arg(type_name(expr.match.ret), ret), var)
            return None

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

        if isinstance(expr, ast.Noop):
            # well, it's noop
            return None

        if isinstance(expr, ast.Deref):
            val = self._gen(expr.expr)
            return self.writer.call('load', type_name(expr.expr_type), val)

        # elif isinstance(expr, ast.Void):
        #     self.writer.instr('pop', self._type(expr.expr.expr_type))

        assert False, f'unknown expr type {expr}'


def type_name(tp: types.Type) -> str:
    if tp == builtin.VOID:
        return 'void'

    if tp == builtin.INT:
        return 'i32'

    if tp == builtin.FLOAT:
        return 'float'

    if tp == builtin.BOOL:
        return 'i1'

    # if isinstance(tp, types.Array):
    #     return f'[{type_name(tp.type)}]'

    if isinstance(tp, types.Reference):
        return type_name(tp.type) + '*'

    # if isinstance(tp, types.Generic):
    #     return tp.fullname()

    # if isinstance(tp, (types.StructType, types.EnumerationType)):
    #     name = tp.symbol.fullname()

    #     if len(tp.generics) > 0:
    #         name += '{' + \
    #             ','.join(type_name(g) for g in tp.generics) + \
    #             '}'

    #     return name

    assert False, tp


def fn_name(fn: symbols.Function) -> str:
    return f'@"{fn.fullname()}"'


def match_name(match: types.Match) -> str:
    fn = match.source
    assert isinstance(fn, symbols.Function)

    return fn_name(fn)


def var_name(var: symbols.Variable) -> str:
    tp = 'a' if var.is_arg else f'l{var.index}'
    return f'%{var.name}_{tp}'


def param_name(param: symbols.Variable) -> str:
    assert param.is_arg
    return f'%{param.name}_p'


def ref_sym(var: symbols.Variable) -> Arg:
    return Arg(type_name(var.var_type()), var_name(var))
