import sys
from lexer import Lexer
from parse import Parser
from symbols import Location, Symbol, Reference
import symbols

class Generator:
    def __init__(self):
        self._gens = {}
        for attr in dir(self):
            if attr[0].isupper():
                self._gens[attr] = getattr(self, attr)

        self._labels = {}

    def generate(self, tree, name, refs, out):
        self.module_name = name
        self.refs = refs
        self.out = out

        self.indent = 0
        self._gen(tree)

    def _write(self, *args):
        self.out.write('  ' * self.indent
                + ' '.join(str(a) for a in args)
                + '\n')

    def _gen(self, node):
        self._write('# {}'.format(node))

        self.indent += 1

        self._gens[node.type](node)
        self._cast(node)

        self.indent -= 1

    def _cast(self, node):
        if node.expr_type is None:
            return

        assert node.target_type is not None

        if node.target_type == symbols.NONE:
            if node.expr_type.size() > 0:
                self._write('pop', node.expr_type.size())

            return

        assert node.expr_type != symbols.NONE

        # TODO: need to change when cast is more than level reduction
        if type(node.expr_type) is not Reference:
            return

        lvl = node.expr_type.level
        tar = symbols.to_ref(node.target_type).level

        while lvl > tar:
            lvl -= 1
            tp = symbols.to_level(node.expr_type, lvl)
            self._write('load', tp.size())

    def _pop_size(self, stack, target):
        size = 0
        while stack is not target:
            assert stack is not None, 'cannot match stack'

            tp_size = stack[0].size()

            assert tp_size > 0
            size += tp_size
            stack = stack[1]

        return size

    def _exit(self, stack, target):
        amount = self._pop_size(stack, target)
        if amount > 0:
            self._write('pop', amount)

    def _reduce(self, stack, target):
        assert symbols.match_type(stack[0], target[0], {})

        size = stack[0].size()
        amount = self._pop_size(stack[1], target[1])

        assert size > 0
        if amount > 0:
            self._write('reduce', size, amount)

    def _label(self, name):
        count = self._labels[name] if name in self._labels else 0
        self._labels[name] = count + 1
        return '{}_{}'.format(name, count)

    def FILE(self, node):
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

        for c in node.children:
            if c.type == 'DEF':
                self._gen(c)
                self._write('')

        for c in node.children:
            if c.type not in ['STRUCT', 'DEF']:
                self._gen(c)
                self._write('')

    def IMPORT(self, node):
        # TODO
        assert False

    def DEF(self, node):
        end = 'END_FN_' + node.function.fullname()

        self._write('function', node.function.fullname(), end)
        self._gen(node.children[2])

        if node.function.ret.size() == 0:
            self._write('return')
        else:
            self._write('return_val', node.function.ret.size())

        self._write(end + ':')
        self._write('')

    def BLOCK(self, node):
        for c in node.children:
            self._gen(c)
            self._write('')

        if node.target_type == symbols.NONE:
            self._exit(node.stack_end, node.parent.stack_start)
        else:
            self._reduce(node.stack_end, node.parent.stack_end)

    def EMPTY(self, node):
        pass

    def LET(self, node):
        if node.children[1].type == 'EMPTY':
            self._write('push', node.sym.type.size())
        else:
            self._gen(node.children[1])

    def IF(self, node):
        els = self._label('ELSE')
        end = self._label('END_IF')
        has_else = node.children[2].type != 'EMPTY'

        self._gen(node.children[0]) # comp
        self._write('br_false', els if has_else else end)
        self._gen(node.children[1])
        if has_else:
            self._write('br', end)
            self._write(els + ':')
            self._gen(node.children[2])
        self._write(end + ':')

    def WHILE(self, node):
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
        self._gen(node.children[0]) # comp
        self._write('br_true', start)
        self._gen(node.children[2]) # else
        self._write(end + ':')

    def BREAK(self, node):
        tar = node.ancestor('WHILE')

        self._gen(node.children[0])

        if node.children[0].target_type.size() == 0:
            self._exit(node.stack_end, tar.stack_start)
        else:
            self._reduce(node.stack_end, tar.stack_end)

        self._write('br', tar.context['break'])

    def CONTINUE(self, node):
        tar = node.ancestor('WHILE')
        self._exit(node.stack_end, tar.stack_start)
        self._write('br', tar.context['continue'])

    def REDO(self, node):
        tar = node.ancestor('WHILE')
        self._exit(node.stack_end, tar.stack_start)
        self._write('br', tar.context['redo'])

    def RETURN(self, node):
        tar = node.ancestor('DEF')

        self._gen(node.children[0])

        if node.children[0].target_type.size() == 0:
            self._exit(node.stack_end, tar.stack_end)
            self._write('return')
        else:
            self._reduce(node.stack_end, tar.stack_end)
            self._write('return_val', node.children[0].target_type.size())

    def TEST(self, node):
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

    def ASSN(self, node):
        self._gen(node.children[0])
        self._gen(node.children[1])

        size = node.children[1].target_type.size()
        self._write('store', size)

    def CALL(self, node):
        if node.match.function.module().name != '':
            for c in node.children:
                self._gen(c)

            self._write('call', node.match.function.fullpath(), node.arg_size)
            return

        val = node.value

        if val == 'alloc':
            size = node.match.gens['T'].size()
            self._write('const_i', size)

            if len(node.children) > 0:
                self._gen(node.children[0]) # size
                self._write('mult_i')

            self._write('alloc')
            return

        if val == 'dealloc':
            self._gen(node.children[0])

            self._write('dealloc')
            return

        if val == 'realloc':
            self._gen(node.children[0])
            self._gen(node.children[1])

            size = node.match.gens['T'].size()
            self._write('const_i', size)
            self._write('mult_i')
            self._write('realloc')
            return

        if val == '[]':
            self._gen(node.children[0])
            self._gen(node.children[1])

            tp = symbols.to_level(node.expr_type, node.expr_type.level - 1)
            self._write('addr_offset', tp.size())
            return

        assn = False

        if len(node.children) == 1:
            if val == '+':
                raise NotImplementedError('unary + not implemented')
            elif val == '-':
                op = 'neg'
            else:
                assert False, 'unknown operator {}'.format(val)

        elif val == '<':
            op = 'lt'
        elif val == '>':
            op = 'gt'
        elif val == '<=':
            op = 'le'
        elif val == '>=':
            op = 'ge'
        elif val == '==':
            op = 'eq'
        elif val == '!=':
            op = 'ne'
        else:
            if val[-1] == '=':
                assn = True
                val = val[:-1]

            if val == '+':
                op = 'add'
            elif val == '-':
                op = 'sub'
            elif val == '*':
                op = 'mult'
            elif val == '/':
                op = 'div'
            elif val == '%':
                op = 'mod'
            else:
                assert False, 'unknown operator {}'.format(val)

        self._gen(node.children[0])

        if assn:
            tp = node.children[0].target_type
            size = tp.type.size()

            self._write('dup', tp.size())
            self._write('load', size)

        if len(node.children) > 1:
            self._gen(node.children[1])

        tp = node.children[0].target_type.fullname()[0].lower()
        self._write('{}_{}'.format(op, tp))

        if assn:
            self._write('store', size)

    def MEMBER(self, node):
        self._gen(node.children[0])

        self._write('offset', node.field.offset)

    def NUM(self, node):
        self._write('const_i', node.value)

    def FLOAT(self, node):
        self._write('const_f', node.value)

    def VAR(self, node):
        if node.sym.TYPE == Symbol.Constant:
            if node.sym.type == symbols.BOOL:
                if node.sym.value:
                    self._write('const_true')
                else:
                    self._write('const_false')
            else:
                raise NotImplementedError()

        elif node.sym.location == Location.Global:
            # self._write('addr_glob', node.sym.offset)
            raise NotImplementedError()

        elif node.sym.location == Location.Param:
            self._write('addr_frame',
                    node.sym.offset)

        elif node.sym.location == Location.Local:
            self._write('addr_frame', node.sym.offset)

        else:
            assert False
