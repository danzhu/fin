from typing import Dict, Set, List, Union
from collections import OrderedDict
from io import TextIOBase
from . import builtin
from . import symbols
from . import types
from . import pattern
from .node import Node


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


class Writer:
    def __init__(self, parent: 'Writer' = None) -> None:
        self._instrs: List[str] = []
        self._indent: int = 0 if parent is None else parent._indent

    def _write(self, val: str) -> None:
        self._instrs.append('  ' * self._indent + val)

    def output(self, out: TextIOBase) -> None:
        for instr in self._instrs:
            out.write(instr + '\n')

    def indent(self) -> None:
        self._indent += 1

    def dedent(self) -> None:
        self._indent -= 1

    def instr(self, *args: str) -> None:
        self._write(' '.join(args))

    def comment(self, val: object) -> None:
        self._write(f'# {val}')

    def label(self, label: str) -> None:
        self._write(f'{label}:')

    def space(self) -> None:
        self._write('')

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
            if tp.symbol == builtin.BOOL_SYM:
                self.instr('size_b')
            elif tp.symbol == builtin.INT_SYM:
                self.instr('size_i')
            elif tp.symbol == builtin.FLOAT_SYM:
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
    def __init__(self, root: Node, out: TextIOBase) -> None:
        self._root = root

        self._labels: Dict[str, int] = {}
        self._function_refs: Set[symbols.Function] = set()
        self._type_refs: Dict[str, SymbolRef] = {}

        body = Writer()
        for c in root.children:
            if c.type == 'IMPORT':
                continue

            if c.type == 'STRUCT':
                Type(self, c.struct, body)
            elif c.type == 'ENUM':
                Type(self, c.enum, body)
            elif c.type == 'DEF':
                Function(self, c, body)
            else:
                raise NotImplementedError()

            body.space()

        writer = Writer()
        writer.instr('lib', quote(root.module.name))
        writer.space()

        ref_mod = None
        for fn in sorted(self._function_refs):
            mod = fn.module()

            if ref_mod != mod:
                writer.instr('ref_lib', quote(mod.fullname()))
                ref_mod = mod

            writer.instr('ref_fn', quote(fn.basename()))

        # FIXME: type need to be in its module
        # writer.space()
        # for tp_name, tp in self._type_refs.items():
        #     writer.instr('ref_type', tp.symbol.fullname())
        #     for mem in tp.member_refs:
        #         writer.instr('ref_mem', quote(mem))

        writer.space()
        writer.extend(body)

        writer.output(out)

    def label(self, name: str) -> str:
        count = self._labels.get(name, 0)
        self._labels[name] = count + 1
        return f'{name}_{count}'

    def ref_function(self, fn: symbols.Function) -> None:
        mod = fn.module()

        # don't ref current module / builtin
        if mod != self._root.module:
            self._function_refs.add(fn)

    def ref_member(self, tp: types.Type, mem: str) -> None:
        assert isinstance(tp, (types.StructType, types.EnumerationType))

        sym = tp.symbol
        mod = sym.module()
        if mod == self._root.module:
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
                 node: Node,
                 writer: Writer) -> None:
        self.gen = gen

        self._temps = 0
        self.types: Dict[str, TypeRef] = {}
        self.contracts: Dict[str, types.Match] = {}
        self.locals: OrderedDict[str, types.Type] = OrderedDict()

        for param in node.function.params:
            self._type(param.type)

        stk = TypeList()
        node.context = {'after': stk.push(node.function.ret)}

        self.writer = Writer(writer)
        self._gen(node.children[3], stk)
        if node.function.ret == builtin.VOID:
            self.writer.instr('end')
        else:
            self.writer.instr('ret', self._type(node.function.ret))

        name = node.function.basename()
        gens = len(node.function.generics)
        ctrs = 0  # TODO: contract bounds

        begin = self.gen.label('BEGIN_FN')
        end = self.gen.label('END_FN')

        writer.comment(node)
        writer.instr('fn', quote(name), str(gens), str(ctrs), begin, end)

        writer.indent()

        writer.comment('types')
        for gen_sym in node.function.generics:
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
        for param in node.function.params:
            writer.instr('!off', var_name(param))
            writer.instr('param', type_name(param.type))
            writer.space()

        writer.space()
        writer.comment('locals')
        for name, local_tp in self.locals.items():
            writer.instr('!off', name)
            writer.instr('local', type_name(local_tp))
            writer.space()

        writer.dedent()
        writer.instr('sign')

        writer.label(begin)
        writer.extend(self.writer)

        writer.label(end)
        writer.space()

    def _temp(self) -> str:
        temp = f't{self._temps}'
        self._temps += 1
        return temp

    def _gen(self, node: Node, stk: TypeList) -> TypeList:
        self.writer.comment(node)

        self.writer.indent()

        getattr(self, f'_{node.type}')(node, stk)
        self._cast(node.expr_type, node.target_type)
        if node.target_type != builtin.VOID and \
                node.target_type != builtin.DIVERGE:
            stk = stk.push(node.target_type)

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
        tp = types.to_level(tp, 0)
        tp_name = self._type(tp)
        name = f'{tp_name}:{mem}'
        self.types[tp_name].ref_member(mem)
        self.gen.ref_member(tp, mem)
        return name

    def _push_local(self, name: str, tp: types.Type) -> None:
        assert name not in self.locals

        self._type(tp)
        self.locals[name] = tp

    def _pop_local(self, name: str) -> None:
        pass

    def _cast(self, tp: types.Type, tar: types.Type) -> None:
        # diverge will never return so we can ignore casting
        if tp is None or tp == builtin.DIVERGE:
            return

        assert tar is not None
        assert tar != builtin.UNKNOWN
        assert tar != builtin.DIVERGE

        if tar == builtin.VOID:
            if tp != builtin.VOID:
                self.writer.instr('pop', self._type(tp))

            return

        assert tp != builtin.UNKNOWN
        assert tp != builtin.VOID

        # TODO: need to change when cast is more than level reduction
        if not isinstance(tp, types.Reference):
            return

        lvl = tp.level
        tar_lvl = types.to_ref(tar).level

        while lvl > tar_lvl:
            lvl -= 1
            tp = types.to_level(tp, lvl)
            self.writer.instr('load', self._type(tp))

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
        self._cast(tp, pat.type)

        if isinstance(pat, pattern.Variable):
            self.writer.instr('store_var',
                              var_name(pat.variable),
                              self._type(pat.type))

        elif isinstance(pat, pattern.Constant):
            if isinstance(pat.value, int):
                self.writer.instr('const_i', str(pat.value))
                self.writer.instr('eq_i')
            elif isinstance(pat.value, float):
                self.writer.instr('const_f', str(pat.value))
                self.writer.instr('eq_f')
            else:
                assert False

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

    def _BLOCK(self, node: Node, stk: TypeList) -> None:
        for c in node.children:
            stk = self._gen(c, stk)
            self.writer.space()

        for var in node.block.locals:
            self._pop_local(var_name(var))

    def _EMPTY(self, node: Node, stk: TypeList) -> None:
        pass

    def _LET(self, node: Node, stk: TypeList) -> None:
        assert isinstance(node.variable, symbols.Variable)

        self._push_local(var_name(node.variable), node.variable.type)
        if node.children[1].type != 'EMPTY':
            self._gen(node.children[1], stk)
            self.writer.instr('store_var',
                              var_name(node.variable),
                              self._type(node.variable.type))

    def _IF(self, node: Node, stk: TypeList) -> None:
        els = self.gen.label('ELSE')
        end = self.gen.label('END_IF')
        has_else = node.children[2].type != 'EMPTY'

        self._gen(node.children[0], stk)  # comp
        self.writer.instr('br_false', els if has_else else end)
        self._gen(node.children[1], stk)

        if has_else:
            self.writer.instr('br', end)
            self.writer.label(els)
            self._gen(node.children[2], stk)

        self.writer.label(end)

    def _MATCH(self, node: Node, stk: TypeList) -> None:
        end = self.gen.label('END_MATCH')

        node.context = {
            'end': end
        }

        self._gen(node.children[0], stk)

        for c in node.children[1].children:
            self._gen(c, stk)

        # no match found
        self.writer.instr('error')
        self.writer.label(end)

    def _ARM(self, node: Node, stk: TypeList) -> None:
        match = node.ancestor('MATCH')

        nxt = self.gen.label('ARM')

        pat = node.children[0].pattern
        tp = match.children[0].target_type

        for var in pat.variables():
            self._push_local(var_name(var.variable), var.variable.type)

        if pat.tested() or pat.bound():
            self.writer.instr('dup', self._type(tp))
            self._match(pat, tp, nxt)

        self.writer.instr('pop', self._type(tp))

        self._gen(node.children[1], stk)

        for var in pat.variables():
            self._pop_local(var_name(var.variable))

        self.writer.instr('br', match.context['end'])
        self.writer.label(nxt)

    def _WHILE(self, node: Node, stk: TypeList) -> None:
        start = self.gen.label('WHILE')
        cond = self.gen.label('COND')
        end = self.gen.label('END_WHILE')

        node.context = {
            'break': end,
            'continue': cond,
            'redo': start,
            'before': stk,
            'after': stk.push(node.target_type)
        }

        self.writer.instr('br', cond)

        self.writer.label(start)
        self._gen(node.children[1], stk)

        self.writer.label(cond)
        self._gen(node.children[0], stk)  # comp
        self.writer.instr('br_true', start)

        self._gen(node.children[2], stk)  # else
        self.writer.label(end)

    def _BREAK(self, node: Node, stk: TypeList) -> None:
        tar = node.ancestor('WHILE')

        stk = self._gen(node.children[0], stk)
        if node.children[0].target_type == builtin.VOID:
            self._exit(stk, tar.context['after'])
        else:
            self._reduce(stk, tar.context['after'])

        self.writer.instr('br', tar.context['break'])

    def _CONTINUE(self, node: Node, stk: TypeList) -> None:
        tar = node.ancestor('WHILE')
        self._exit(stk, tar.context['before'])
        self.writer.instr('br', tar.context['continue'])

    def _REDO(self, node: Node, stk: TypeList) -> None:
        tar = node.ancestor('WHILE')
        self._exit(stk, tar.context['before'])
        self.writer.instr('br', tar.context['redo'])

    def _RETURN(self, node: Node, stk: TypeList) -> None:
        tar = node.ancestor('DEF')

        stk = self._gen(node.children[0], stk)

        # TODO: cleanup variables for RAII
        if node.children[0].target_type == builtin.VOID:
            self.writer.instr('end')
        else:
            self.writer.instr('ret', self._type(tar.function.ret))

    def _TEST(self, node: Node, stk: TypeList) -> None:
        if node.value == 'NOT':
            self._gen(node.children[0], stk)
            self.writer.instr('not')
            return

        jump = self.gen.label('SHORT_CIRCUIT')
        end = self.gen.label('END_TEST')

        self._gen(node.children[0], stk)

        if node.value == 'AND':
            self.writer.instr('br_false', jump)
        else:
            self.writer.instr('br_true', jump)

        self._gen(node.children[1], stk)
        self.writer.instr('br', end)
        self.writer.label(jump)

        if node.value == 'AND':
            self.writer.instr('const_false')
        else:
            self.writer.instr('const_true')

        self.writer.label(end)

    def _ASSN(self, node: Node, stk: TypeList) -> None:
        stk = self._gen(node.children[0], stk)
        stk = self._gen(node.children[1], stk)

        tp = node.children[1].target_type
        self.writer.instr('store', self._type(tp))

    def _CALL(self, node: Node, stk: TypeList) -> None:
        sym = node.match.source

        if isinstance(sym, symbols.Function):
            for c in node.children[1].children:
                stk = self._gen(c, stk)

            self._call(node.match)

        elif isinstance(sym, (symbols.Struct, symbols.Variant)):
            tmp = self._temp()

            tp = node.match.ret
            self._push_local(tmp, tp)

            assert isinstance(tp, (types.StructType, types.EnumerationType))

            if isinstance(sym, symbols.Variant):
                self.writer.instr('addr_var', tmp)
                # TODO: user-defined value type
                self.writer.instr('const_i', str(sym.value))
                self.writer.instr('store_mem',
                                  self._member(tp, '_value'),
                                  self._type(builtin.INT))

            # silence type checker
            assert isinstance(sym, (symbols.Struct, symbols.Variant))

            assert len(node.children[1].children) == len(sym.fields)

            for child, field in zip(node.children[1].children, sym.fields):
                self.writer.instr('addr_var', tmp)
                self._gen(child, stk)
                self.writer.instr('store_mem',
                                  self._member(tp, field.name),
                                  self._type(child.target_type))

            self.writer.instr('load_var', tmp, self._type(tp))
            self._pop_local(tmp)

        else:
            assert False

    def _OP(self, node: Node, stk: TypeList) -> None:
        for c in node.children:
            stk = self._gen(c, stk)

        self._call(node.match)

    def _INC_ASSN(self, node: Node, stk: TypeList) -> None:
        # left
        stk = self._gen(node.children[0], stk)
        tp = node.children[0].target_type
        self.writer.instr('dup', self._type(tp))
        self._cast(node.children[0].target_type, node.match.params[0].type)

        # right
        stk = self._gen(node.children[1], stk)

        # call
        self._call(node.match)

        # assn
        ret = types.to_level(node.children[0].target_type, 0)
        self._cast(node.match.ret, ret)
        self.writer.instr('store', self._type(ret))

    def _CAST(self, node: Node, stk: TypeList) -> None:
        self._gen(node.children[0], stk)
        self._call(node.match)

    def _MEMBER(self, node: Node, stk: TypeList) -> None:
        assert isinstance(node.variable, symbols.Variable)

        self._gen(node.children[0], stk)

        tp = node.children[0].target_type
        mem = node.children[1].value
        self.writer.instr('addr_mem', self._member(tp, mem))

    def _NUM(self, node: Node, stk: TypeList) -> None:
        self.writer.instr('const_i', node.value)

    def _FLOAT(self, node: Node, stk: TypeList) -> None:
        self.writer.instr('const_f', node.value)

    def _VAR(self, node: Node, stk: TypeList) -> None:
        if isinstance(node.variable, symbols.Constant):
            tp = node.variable.type
            if not isinstance(tp, types.StructType):
                raise NotImplementedError()

            if isinstance(node.variable.value, bool):
                if node.variable.value:
                    self.writer.instr('const_true')
                else:
                    self.writer.instr('const_false')
            else:
                raise NotImplementedError()

        elif isinstance(node.variable, symbols.Variable):
            if node.variable.is_arg:
                self.writer.instr('addr_arg', var_name(node.variable))
            else:
                self.writer.instr('addr_var', var_name(node.variable))

        else:
            assert False


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
