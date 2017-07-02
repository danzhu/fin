from typing import Any, Dict, Set, cast
from io import TextIOBase
from .reflect import Reference, Variable, Constant, Function, Struct, Type, \
    Match, StructType, Variant, Enumeration, EnumerationType
from . import symbols
from . import pattern
from .node import Node, StackNode


class Generator:
    def __init__(self) -> None:
        self._labels: Dict[str, int] = {}
        self.module_name: str = None
        self.refs: Set[Function] = None
        self.out: TextIOBase = None
        self.indent: int = None

    def generate(self,
                 tree: Node,
                 name: str,
                 refs: Set[Function],
                 out: TextIOBase) -> None:
        self.module_name = name
        self.refs = refs
        self.out = out

        self.indent = 0
        self._gen(tree)

    def _write(self, *args: Any) -> None:
        self.out.write('  ' * self.indent +
                       ' '.join(str(a) for a in args) +
                       '\n')

    def _gen(self, node: Node) -> None:
        self._write(f'# {node}')

        self.indent += 1

        getattr(self, f'_{node.type}')(node)
        self._cast(node.expr_type, node.target_type)

        self.indent -= 1

    def _cast(self, tp: Type, tar: Type) -> None:
        # diverge will never return so we can ignore casting
        if tp is None or tp == symbols.DIVERGE:
            return

        assert tar is not None
        assert tar != symbols.UNKNOWN
        assert tar != symbols.DIVERGE

        if tar == symbols.VOID:
            if tp != symbols.VOID and tp.size() > 0:
                self._write('pop', tp.size())

            return

        assert tp != symbols.UNKNOWN
        assert tp != symbols.VOID

        # TODO: need to change when cast is more than level reduction
        if not isinstance(tp, Reference):
            return

        lvl = tp.level
        tar_lvl = symbols.to_ref(tar).level

        while lvl > tar_lvl:
            lvl -= 1
            tp = symbols.to_level(tp, lvl)
            self._write('load', tp.size())

    def _pop_size(self, stack: StackNode, target: StackNode) -> int:
        size = 0
        while stack is not target:
            assert stack is not None, 'cannot match stack'

            tp_size = stack.type.size()

            assert tp_size > 0
            size += tp_size
            stack = stack.next

        return size

    def _exit(self, stack: StackNode, target: StackNode) -> None:
        amount = self._pop_size(stack, target)
        if amount > 0:
            self._write('pop', amount)

    def _reduce(self, stack: StackNode, target: StackNode) -> None:
        assert symbols.match_type(target.type, stack.type, {})

        size = stack.type.size()
        amount = self._pop_size(stack.next, target.next)

        assert size > 0
        if amount > 0:
            self._write('reduce', size, amount)

    def _label(self, name: str) -> str:
        count = self._labels[name] if name in self._labels else 0
        self._labels[name] = count + 1
        return f'{name}_{count}'

    def _call(self, match: Match) -> None:
        assert isinstance(match.source, Function)

        fn: Function = match.source

        # user-defined function
        if fn.module().name != '':
            arg_size = sum(p.size() for p in match.args)
            self._write('call', fn.fullpath(), arg_size)
            return

        if fn.name == 'alloc':
            size = match.resolved_gens['T'].size()
            self._write('const_i', size)

            if len(fn.params) > 0:
                self._write('mult_i')

            self._write('alloc')
            return

        if fn.name == 'dealloc':
            self._write('dealloc')
            return

        if fn.name == 'realloc':
            tp = match.resolved_gens['T']
            self._write('const_i', tp.size())
            self._write('mult_i')
            self._write('realloc')
            return

        if fn.name == 'subscript':
            tp = match.resolved_gens['T']
            self._write('addr_offset', tp.size())
            return

        if fn.name == 'cast':
            frm = match.args[0].fullname()[0].lower()
            tar = match.result.fullname()[0].lower()
            self._write(f'cast_{frm}_{tar}')
            return

        if fn.name == 'pos':
            raise NotImplementedError('unary + not implemented')
        elif fn.name == 'neg':
            op = 'neg'
        elif fn.name == 'less':
            op = 'lt'
        elif fn.name == 'greater':
            op = 'gt'
        elif fn.name == 'lessEqual':
            op = 'le'
        elif fn.name == 'greaterEqual':
            op = 'ge'
        elif fn.name == 'equal':
            op = 'eq'
        elif fn.name == 'notEqual':
            op = 'ne'
        elif fn.name == 'plus':
            op = 'add'
        elif fn.name == 'minus':
            op = 'sub'
        elif fn.name == 'multiplies':
            op = 'mult'
        elif fn.name == 'divides':
            op = 'div'
        elif fn.name == 'modulus':
            op = 'mod'
        else:
            assert False, f'unknown operator {fn.name}'

        name = match.args[0].fullname()[0].lower()
        self._write(f'{op}_{name}')

    def _match(self, pat: pattern.Pattern, tp: Type, nxt: str) -> None:
        self._write(f'# match {pat}')
        self._cast(tp, pat.type)

        if isinstance(pat, pattern.Int):
            self._write('const_i', pat.value)
            self._write('eq_i')
            self._write('br_false', nxt)

        elif isinstance(pat, pattern.Float):
            self._write('const_f', pat.value)
            self._write('eq_f')
            self._write('br_false', nxt)

        elif isinstance(pat, pattern.Variant):
            assert isinstance(pat.type, EnumerationType)

            fail = self._label('MATCH_FAIL')
            succ = self._label('MATCH_SUCC')
            size = pat.type.size()  # size of enum

            self._write('addr_st', -size)
            self._write('load', pat.type.enum.size)  # int of variant
            self._write('const_i', pat.variant.value)
            self._write('eq_i')
            self._write('br_false', fail)

            self.indent += 1
            for p, var in zip(pat.fields, pat.variant_struct.resolved_fields):
                if not p.TESTED:
                    continue

                self._match(p, var.type, fail)

            self.indent -= 1

            self._write('br', succ)

            self._write(f'{fail}:')
            self._write('pop', size)
            self._write('br', nxt)

            self._write(f'{succ}:')
            self._write('pop', size)

        else:
            assert False

    def _destructure(self, pat: pattern.Pattern, tp: Type) -> int:
        self._write(f'# destructure {pat}')

        if isinstance(pat, (pattern.Int, pattern.Float, pattern.Any)):
            self._write('pop', tp.size())
            return 0

        self._cast(tp, pat.type)

        if isinstance(pat, pattern.Variable):
            return pat.type.size()

        if isinstance(pat, pattern.Variant):
            assert isinstance(pat.type, EnumerationType)

            src_size = pat.type.size()
            red_size = 0

            self.indent += 1
            for p, var in zip(pat.fields, pat.variant_struct.resolved_fields):
                if not p.BOUND:
                    continue

                offset = var.offset - src_size
                self._write('addr_st', offset)
                self._write('load', var.type.size())
                red_size += self._destructure(p, var.type)

            self.indent -= 1

            if red_size > 0:
                self._write('reduce', red_size, src_size)
            else:
                self._write('pop', src_size)
            return red_size

        assert False

    def _FILE(self, node: Node) -> None:
        ref_list = []
        for ref in self.refs:
            mod = ref.module()

            # don't ref current module / builtin
            if mod != node.module and mod.name != '':
                ref_list.append((mod, ref.fullname()))

        ref_list.sort()

        self._write('module', self.module_name)

        module = None
        for mod, fn in ref_list:
            if module != mod:
                self._write('ref_module', mod.name)
                module = mod

            self._write('ref_function', fn)

        self._write('')

        for c in node.children:
            if c.type == 'DEF':
                self._gen(c)
                self._write('')

        for c in node.children:
            if c.type not in ['IMPORT', 'STRUCT', 'ENUM', 'DEF']:
                self._gen(c)
                self._write('')

    def _DEF(self, node: Node) -> None:
        end = 'END_FN_' + node.function.fullname()

        self._write('function', node.function.fullname(), end)
        self._gen(node.children[2])

        if node.function.ret == symbols.VOID:
            self._write('return')
        else:
            self._write('return_val', node.function.ret.size())

        self._write(end + ':')
        self._write('')

    def _BLOCK(self, node: Node) -> None:
        for c in node.children:
            self._gen(c)
            self._write('')

        if node.target_type == symbols.VOID:
            self._exit(node.stack_end, node.parent.stack_start)
        else:
            self._reduce(node.stack_end, node.parent.stack_end)

    def _EMPTY(self, node: Node) -> None:
        pass

    def _LET(self, node: Node) -> None:
        if node.children[1].type == 'EMPTY':
            self._write('push', node.variable.type.size())
        else:
            self._gen(node.children[1])

    def _IF(self, node: Node) -> None:
        els = self._label('ELSE')
        end = self._label('END_IF')
        has_else = node.children[2].type != 'EMPTY'

        self._gen(node.children[0])  # comp
        self._write('br_false', els if has_else else end)
        self._gen(node.children[1])

        if has_else:
            self._write('br', end)
            self._write(els + ':')
            self._gen(node.children[2])

        self._write(end + ':')

    def _MATCH(self, node: Node) -> None:
        end = self._label('END_MATCH')

        node.context = {
            'end': end
        }

        self._gen(node.children[0])

        for c in node.children[1].children:
            self._gen(c)

        # pop value if unmatched
        # TODO: maybe error?
        self._write('pop', node.children[0].target_type.size())
        self._write(end + ':')

    def _ARM(self, node: Node) -> None:
        match = node.ancestor('MATCH')

        nxt = self._label('ARM')

        pat = node.children[0].pattern
        tp = match.children[0].target_type

        if pat.TESTED:
            self._write('dup', tp.size())
            self._match(pat, tp, nxt)

        self._destructure(pat, tp)

        self._gen(node.children[1])

        self._write('br', match.context['end'])
        self._write(nxt + ':')

    def _WHILE(self, node: Node) -> None:
        start = self._label('WHILE')
        cond = self._label('COND')
        end = self._label('END_WHILE')

        node.context = {
            'break': end,
            'continue': cond,
            'redo': start
        }

        self._write('br', cond)
        self._write(start + ':')
        self._gen(node.children[1])
        self._write(cond + ':')
        self._gen(node.children[0])  # comp
        self._write('br_true', start)
        self._gen(node.children[2])  # else
        self._write(end + ':')

    def _BREAK(self, node: Node) -> None:
        tar = node.ancestor('WHILE')

        self._gen(node.children[0])

        if node.children[0].target_type == symbols.VOID:
            self._exit(node.stack_end, tar.stack_start)
        else:
            self._reduce(node.stack_end, tar.stack_end)

        self._write('br', tar.context['break'])

    def _CONTINUE(self, node: Node) -> None:
        tar = node.ancestor('WHILE')
        self._exit(node.stack_end, tar.stack_start)
        self._write('br', tar.context['continue'])

    def _REDO(self, node: Node) -> None:
        tar = node.ancestor('WHILE')
        self._exit(node.stack_end, tar.stack_start)
        self._write('br', tar.context['redo'])

    def _RETURN(self, node: Node) -> None:
        tar = node.ancestor('DEF')

        self._gen(node.children[0])

        if node.children[0].target_type == symbols.VOID:
            self._exit(node.stack_end, tar.stack_end)
            self._write('return')
        else:
            self._reduce(node.stack_end, tar.stack_end)
            self._write('return_val', node.children[0].target_type.size())

    def _TEST(self, node: Node) -> None:
        if node.value == 'NOT':
            self._gen(node.children[0])
            self._write('not')
            return

        jump = self._label('SHORT_CIRCUIT')
        end = self._label('END_TEST')

        self._gen(node.children[0])

        if node.value == 'AND':
            self._write('br_false', jump)
        else:
            self._write('br_true', jump)

        self._gen(node.children[1])
        self._write('br', end)
        self._write(jump + ':')

        if node.value == 'AND':
            self._write('const_false')
        else:
            self._write('const_true')

        self._write(end + ':')

    def _ASSN(self, node: Node) -> None:
        self._gen(node.children[0])
        self._gen(node.children[1])

        size = node.children[1].target_type.size()
        self._write('store', size)

    def _CALL(self, node: Node) -> None:
        if isinstance(node.match.source, Variant):
            self._write('const_i', node.match.source.value)

        for c in node.children[1].children:
            self._gen(c)

        if isinstance(node.match.source, Function):
            self._call(node.match)
        elif isinstance(node.match.source, Struct):
            pass  # struct construction
        elif isinstance(node.match.source, Variant):
            enum = cast(Enumeration, node.match.source.parent).size
            args = sum(c.target_type.size() for c in node.children[1].children)
            size = node.target_type.size() - enum - args
            if size > 0:
                self._write('push', size)
        else:
            assert False

    def _OP(self, node: Node) -> None:
        for c in node.children:
            self._gen(c)

        self._call(node.match)

    def _INC_ASSN(self, node) -> None:
        # left
        self._gen(node.children[0])
        self._write('dup', node.children[0].target_type.size())
        self._cast(node.children[0].target_type, node.match.params[0])

        # right
        self._gen(node.children[1])

        # call
        self._call(node.match)

        # assn
        ret = symbols.to_level(node.children[0].target_type, 0)
        self._cast(node.match.ret, ret)
        self._write('store', ret.size())

    def _CAST(self, node: Node) -> None:
        self._gen(node.children[0])
        self._call(node.match)

    def _MEMBER(self, node: Node) -> None:
        assert isinstance(node.variable, Variable)

        self._gen(node.children[0])

        if node.variable.offset > 0:
            self._write('offset', node.variable.offset)

    def _NUM(self, node: Node) -> None:
        self._write('const_i', node.value)

    def _FLOAT(self, node: Node) -> None:
        self._write('const_f', node.value)

    def _VAR(self, node: Node) -> None:
        if isinstance(node.variable, Constant):
            cons = node.variable.type
            if not isinstance(cons, StructType):
                raise NotADirectoryError()

            if cons.struct == symbols.BOOL:
                if node.variable.value:
                    self._write('const_true')
                else:
                    self._write('const_false')
            else:
                raise NotImplementedError()

        elif isinstance(node.variable, Variable):
            self._write('addr_frame', node.variable.offset)

        else:
            assert False
