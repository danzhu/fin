from typing import Any, Dict, Set, List, Sequence, Iterable, Iterator, Union, \
    Tuple, Sized, TypeVar, Generic, cast
from collections import OrderedDict
from io import TextIOBase
from . import builtin
from . import symbols
from . import types
from . import pattern
from .node import Node


T = TypeVar('T')


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

    def instr(self, *args: object) -> None:
        self._write(' '.join(str(a) for a in args))

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
            self.type(tp.type)
            self.instr('size_arr', 0 if tp.length is None else tp.length)

        elif isinstance(tp, types.Generic):
            self.instr('size_dup', tp.symbol.index)

        elif isinstance(tp, types.Special):
            assert False, 'when?'

        elif isinstance(tp, types.StructType):
            if tp.struct == builtin.BOOL_SYM:
                self.instr('size_b')
            elif tp.struct == builtin.INT_SYM:
                self.instr('size_i')
            elif tp.struct == builtin.FLOAT_SYM:
                self.instr('size_f')
            else:
                for gen in tp.generics:
                    self.type(gen)

                self.instr('type_call', tp.struct.fullname())

        else:
            assert False, f'unknown type {tp}'

    def contract(self, ctr: types.Match) -> None:
        assert isinstance(ctr.source, symbols.Function)

        for gen in ctr.generics:
            self.type(gen)

        self.instr('contract', ctr.source.fullname())


class KeyList(Generic[T], Iterable[T], Sized):
    def __init__(self) -> None:
        self.keys: Set[str] = set()
        self.values: List[T] = []

    def __len__(self) -> int:
        return len(self.values)

    def __iter__(self) -> Iterator[T]:
        return iter(self.values)

    def __getitem__(self, key: int) -> T:
        return self.values[key]

    def add(self, key: str, val: T) -> bool:
        if key in self.keys:
            return False

        self.keys.add(key)
        self.values.append(val)
        return True


class SymbolRef:
    def __init__(self, sym: Union[symbols.Struct, symbols.Enumeration]) -> None:
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
        sym: Union[symbols.Struct, symbols.Enumeration]
        if isinstance(tp, types.StructType):
            sym = tp.struct
        elif isinstance(tp, types.EnumerationType):
            sym = tp.enum
        else:
            assert False

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

        fields: Iterable[symbols.Variable]
        if isinstance(sym, symbols.Struct):
            fields = sym.fields
        elif isinstance(sym, symbols.Enumeration):
            assert False, 'TODO'
        else:
            assert False

        for field in fields:
            self._type(field.type)

        end = gen.label('END_TYPE')

        name = sym.basename()
        gens = len(sym.generics)

        writer.comment(str(sym))
        writer.instr('type', quote(name), gens, end)

        writer.indent()

        writer.comment('types')
        for gen_sym in sym.generics:
            writer.instr('!sz', gen_sym.fullname())
            writer.space()

        for tp_name, tp in sorted(self.types.items()):
            writer.instr('!sz', type_name(tp))
            writer.type(tp)
            writer.space()

        writer.space()
        writer.comment('fields')
        for field in fields:
            writer.instr('field', type_name(field.type))

        writer.dedent()
        writer.instr('type_ret')
        writer.label(end)

        writer.indent()
        for field in fields:
            writer.instr('member', quote(field.name))

        writer.dedent()
        writer.space()

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

        self.writer = Writer(writer)
        self._gen(node.children[3])
        if node.function.ret == builtin.VOID:
            self.writer.instr('end')
        else:
            self.writer.instr('ret', self._type(node.function.ret))

        name = node.function.basename()
        gens = len(node.function.generics)
        ctrs = 0 # TODO: contract bounds

        begin = self.gen.label('BEGIN_FN')
        end = self.gen.label('END_FN')

        writer.comment(node)
        writer.instr('fn', quote(name), gens, ctrs, begin, end)

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

            if isinstance(tp.type, types.StructType):
                name = tp.type.struct.fullname()
            elif isinstance(tp.type, types.EnumerationType):
                name = tp.type.enum.fullname()
            else:
                assert False

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
            writer.instr('!off', param.name)
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
        temp = f'{self._temps}_'
        self._temps += 1
        return temp

    def _gen(self, node: Node) -> None:
        self.writer.comment(node)

        self.writer.indent()

        getattr(self, f'_{node.type}')(node)
        self._cast(node.expr_type, node.target_type)

        self.writer.dedent()

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

    def _exit(self, node: Node, tar: Node) -> None:
        # FIXME: broken in inline struct construction

        has_val = node.target_type != builtin.VOID
        assert not has_val, 'TODO'

        while node is not tar:
            assert node.parent is not None, 'cannot match stack'

            if node.parent.type in ('IF', 'WHILE', 'MATCH'):
                node = node.parent
                continue

            before = False
            for child in reversed(node.parent.children):
                if before:
                    if child.target_type is not None \
                            and child.target_type != builtin.VOID:
                        self.writer.instr('pop', self._type(child.target_type))

                    continue

                if child is node:
                    before = True

            # TODO: RAII cleanup for local variables

            node = node.parent

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
        self.writer.instr(f'# match {pat}')
        self._cast(tp, pat.type)

        if isinstance(pat, pattern.Constant):
            if isinstance(pat.value, int):
                self.writer.instr('const_i', pat.value)
                self.writer.instr('eq_i')
            elif isinstance(pat.value, float):
                self.writer.instr('const_f', pat.value)
                self.writer.instr('eq_f')
            else:
                assert False

            self.writer.instr('br_false', nxt)

        elif isinstance(pat, pattern.Struct):
            fail = self._label('MATCH_FAIL')
            succ = self._label('MATCH_SUCC')
            size = pat.type.size()

            if isinstance(pat.type, types.EnumerationType):
                assert isinstance(pat.source, symbols.Variant)

                self.writer.instr('addr_st', -size)
                self.writer.instr('load', pat.type.enum.size)  # int of variant
                self.writer.instr('const_i', pat.source.value)
                self.writer.instr('eq_i')
                self.writer.instr('br_false', fail)
            else:
                assert isinstance(pat.type, types.StructType)

            src_size = pat.type.size()

            self._indent += 1
            for p, var in zip(pat.subpatterns, pat.fields):
                if not p.tested():
                    continue

                offset = var.offset - src_size
                self.writer.instr('addr_st', offset)
                self.writer.instr('load', var.type.size())
                self._match(p, var.type, fail)

            self._indent -= 1

            self.writer.instr('br', succ)

            self.writer.instr(f'{fail}:')
            self.writer.instr('pop', size)
            self.writer.instr('br', nxt)

            self.writer.instr(f'{succ}:')
            self.writer.instr('pop', size)

        else:
            assert False

    def _destructure(self, pat: pattern.Pattern, tp: types.Type) -> int:
        self.writer.instr(f'# destructure {pat}')
        self._cast(tp, pat.type)

        if isinstance(pat, pattern.Variable):
            return pat.type.size()

        if isinstance(pat, pattern.Struct):
            # note: works for both structs and enums

            src_size = pat.type.size()
            red_size = 0

            self._indent += 1
            for p, var in zip(pat.subpatterns, pat.fields):
                if not p.bound():
                    continue

                # skip what we put on the stack,
                # go back to the start of the struct / enum,
                # and move forward to the field offset
                offset = var.offset - src_size - red_size
                self.writer.instr('addr_st', offset)
                self.writer.instr('load', var.type.size())
                red_size += self._destructure(p, var.type)

            self._indent -= 1

            assert red_size != 0
            self.writer.instr('reduce', red_size, src_size)

            return red_size

        assert False

    def _BLOCK(self, node: Node) -> None:
        for c in node.children:
            self._gen(c)
            self.writer.space()

        for var in node.block.locals:
            self._pop_local(var.name)

    def _EMPTY(self, node: Node) -> None:
        pass

    def _LET(self, node: Node) -> None:
        assert isinstance(node.variable, symbols.Variable)

        self._push_local(node.variable.name, node.variable.type)
        if node.children[1].type != 'EMPTY':
            self.writer.instr('addr_var', node.variable.name)
            self._gen(node.children[1])
            self.writer.instr('store', self._type(node.variable.type))

    def _IF(self, node: Node) -> None:
        els = self.gen.label('ELSE')
        end = self.gen.label('END_IF')
        has_else = node.children[2].type != 'EMPTY'

        self._gen(node.children[0])  # comp
        self.writer.instr('br_false', els if has_else else end)
        self._gen(node.children[1])

        if has_else:
            self.writer.instr('br', end)
            self.writer.label(els)
            self._gen(node.children[2])

        self.writer.label(end)

    def _MATCH(self, node: Node) -> None:
        end = self.gen.label('END_MATCH')

        node.context = {
            'end': end
        }

        self._gen(node.children[0])

        for c in node.children[1].children:
            self._gen(c)

        # no match found
        self.writer.instr('error')
        self.writer.instr(end + ':')

    def _ARM(self, node: Node) -> None:
        match = node.ancestor('MATCH')

        nxt = self.gen.label('ARM')

        pat = node.children[0].pattern
        tp = match.children[0].target_type

        if pat.tested():
            self.writer.instr('dup', self._type(tp))
            self._match(pat, tp, nxt)

        if pat.bound():
            self._destructure(pat, tp)
        else:
            self.writer.instr('pop', self._type(tp))

        self._gen(node.children[1])

        self.writer.instr('br', match.context['end'])
        self.writer.instr(nxt + ':')

    def _WHILE(self, node: Node) -> None:
        start = self.gen.label('WHILE')
        cond = self.gen.label('COND')
        end = self.gen.label('END_WHILE')

        node.context = {
            'break': end,
            'continue': cond,
            'redo': start
        }

        self.writer.instr('br', cond)

        self.writer.label(start)
        self._gen(node.children[1])

        self.writer.label(cond)
        self._gen(node.children[0])  # comp
        self.writer.instr('br_true', start)

        self._gen(node.children[2])  # else
        self.writer.label(end)

    def _BREAK(self, node: Node) -> None:
        tar = node.ancestor('WHILE')

        self._gen(node.children[0])
        self._exit(node.children[0], tar)

        self.writer.instr('br', tar.context['break'])

    def _CONTINUE(self, node: Node) -> None:
        tar = node.ancestor('WHILE')
        self._exit(node, tar)
        self.writer.instr('br', tar.context['continue'])

    def _REDO(self, node: Node) -> None:
        tar = node.ancestor('WHILE')
        self._exit(node, tar)
        self.writer.instr('br', tar.context['redo'])

    def _RETURN(self, node: Node) -> None:
        tar = node.ancestor('DEF')

        self._gen(node.children[0])
        # TODO: popping not necessary when no RAII needed
        self._exit(node.children[0], tar)

        if node.children[0].target_type == builtin.VOID:
            self.writer.instr('end')
        else:
            self.writer.instr('ret')

    def _TEST(self, node: Node) -> None:
        if node.value == 'NOT':
            self._gen(node.children[0])
            self.writer.instr('not')
            return

        jump = self.gen.label('SHORT_CIRCUIT')
        end = self.gen.label('END_TEST')

        self._gen(node.children[0])

        if node.value == 'AND':
            self.writer.instr('br_false', jump)
        else:
            self.writer.instr('br_true', jump)

        self._gen(node.children[1])
        self.writer.instr('br', end)
        self.writer.label(jump)

        if node.value == 'AND':
            self.writer.instr('const_false')
        else:
            self.writer.instr('const_true')

        self.writer.label(end)

    def _ASSN(self, node: Node) -> None:
        self._gen(node.children[0])
        self._gen(node.children[1])

        tp = node.children[1].target_type
        self.writer.instr('store', self._type(tp))

    def _CALL(self, node: Node) -> None:
        if isinstance(node.match.source, symbols.Function):
            for c in node.children[1].children:
                self._gen(c)

            self._call(node.match)

        elif isinstance(node.match.source, symbols.Struct):
            tmp = self._temp()

            tp = node.match.ret
            self._push_local(tmp, tp)

            for i in range(len(node.children[1].children)):
                child = node.children[1].children[i]
                mem = self._member(tp, node.match.source.fields[i].name)

                self.writer.instr('addr_var', tmp)
                self.writer.instr('addr_mem', mem)
                self._gen(child)
                self.writer.instr('store', self._type(child.target_type))

            self.writer.instr('addr_var', tmp)
            self.writer.instr('load', self._type(tp))
            self._pop_local(tmp)

        elif isinstance(node.match.source, symbols.Variant):
            # FIXME: fill variant
            # enum = cast(symbols.Enumeration, node.match.source.parent).size
            # args = sum(c.target_type.size() for c in node.children[1].children)
            # size = node.target_type.size() - enum - args
            # if size > 0:
            #     self.writer.instr('push', size)
            assert False

        else:
            assert False

    def _OP(self, node: Node) -> None:
        for c in node.children:
            self._gen(c)

        self._call(node.match)

    def _INC_ASSN(self, node: Node) -> None:
        # left
        self._gen(node.children[0])
        tp = node.children[0].target_type
        self.writer.instr('dup', self._type(tp))
        self._cast(node.children[0].target_type, node.match.params[0].type)

        # right
        self._gen(node.children[1])

        # call
        self._call(node.match)

        # assn
        ret = types.to_level(node.children[0].target_type, 0)
        self._cast(node.match.ret, ret)
        self.writer.instr('store', self._type(ret))

    def _CAST(self, node: Node) -> None:
        self._gen(node.children[0])
        self._call(node.match)

    def _MEMBER(self, node: Node) -> None:
        assert isinstance(node.variable, symbols.Variable)

        self._gen(node.children[0])

        tp = node.children[0].target_type
        mem = node.children[1].value
        self.writer.instr('addr_mem', self._member(tp, mem))

    def _NUM(self, node: Node) -> None:
        self.writer.instr('const_i', node.value)

    def _FLOAT(self, node: Node) -> None:
        self.writer.instr('const_f', node.value)

    def _VAR(self, node: Node) -> None:
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
            # FIXME: variable names are not unique, this causes conflicts
            if node.variable.is_arg:
                self.writer.instr('addr_arg', node.variable.name)
            else:
                self.writer.instr('addr_var', node.variable.name)

        else:
            assert False


def type_name(tp: types.Type) -> str:
    if isinstance(tp, types.Array):
        return f'[{type_name(tp.type)}]'

    if isinstance(tp, types.Reference):
        return '&'

    if isinstance(tp, types.Generic):
        return tp.fullname()

    if isinstance(tp, types.StructType):
        name = tp.struct.fullname()
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


def quote(s: str) -> str:
    return f"'{s}'"


def native_type_name(tp: types.Type) -> str:
    return tp.fullname()[0].lower()
