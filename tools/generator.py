#!/usr/bin/env python3

import sys
from lexer import Lexer
from parse import Parser
from symbol import Location, Symbol
import symbol

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
        self.indent -= 1

    def _cast(self, node):
        tp = node.expr_type
        tar = node.target_type

        assert tar

        if not tar.none():
            assert not tp.none()

            l = tp.level
            while l > tar.level:
                l -= 1
                self._write('load', tp.size(l))

        elif not tp.empty():
            self._write('pop', tp.size())

    def _label(self, name):
        count = self._labels[name] if name in self._labels else 0
        self._labels[name] = count + 1
        return '{}_{}'.format(name, count)

    def FILE(self, node):
        ref_list = []
        for ref in self.refs:
            mod = ref.ancestor(Symbol.Module)
            if mod != node.module:
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
        pass

    def DEF(self, node):
        end = 'END_FN_' + node.function.fullname()

        self._write('function', node.function.fullname(), end)
        self._gen(node.children[3])

        if node.function.ret.none():
            self._write('return')
        else:
            self._write('return_val', node.function.ret.size())

        self._write(end + ':')
        self._write('')

    def BLOCK(self, node):
        for c in node.children:
            self._gen(c)
            self._write('')

        self._cast(node)

        # pop variables declared in block
        # TODO: RAII
        size = node.block.offset
        if size > 0:
            if node.expr_type.none():
                self._write('pop', size)
            else:
                self._write('reduce', node.target_type.size(), size)

    def LET(self, node):
        # self._write('# let {}'.format(node.sym.name))
        if node.children[2].type == 'EMPTY':
            self._write('push', node.sym.type.size())
        else:
            self._gen(node.children[2])

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

        self._cast(node)

    def WHILE(self, node):
        start = self._label('WHILE')
        cond = self._label('COND')

        self._write('br', cond)
        self._write(start + ':')
        self._gen(node.children[1])
        self._write(cond + ':')
        self._gen(node.children[0]) # comp
        self._write('br_true', start)

        self._cast(node)

    def RETURN(self, node):
        self._cast(node)

        if len(node.children) == 0:
            self._write('return')
        else:
            self._gen(node.children[0])
            self._write('return_val', node.children[0].target_type.size())

    def TEST(self, node):
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

        self._cast(node)

    def ASSN(self, node):
        self._gen(node.children[1]) # value
        self._gen(node.children[0]) # id

        self._write('store', node.children[0].expr_type.size(node.level))

        self._cast(node)

    def INC_ASSN(self, node):
        size = node.children[0].expr_type.size(0)

        self._gen(node.children[0])
        self._write('load', size)
        self._gen(node.children[1])

        op = node.value.split('_', 1)[0].lower()
        tp = node.children[0].expr_type.cls.name[0].lower()
        self._write('{}_{}'.format(op, tp))

        # FIXME: re-evaluation of children is problematic
        self._gen(node.children[0])
        self._write('store', size)

        self._cast(node)

    def CALL(self, node):
        for c in node.children[0].children:
            self._gen(c)

        self._write('call', node.function.fullpath(), node.arg_size)

        self._cast(node)

    def METHOD(self, node):
        self._gen(node.children[0])
        for c in node.children[1].children:
            self._gen(c)

        self._write('call', node.function.fullpath(), node.arg_size)

        self._cast(node)

    def MEMBER(self, node):
        self._gen(node.children[0])

        self._write('offset', node.field.offset)

        self._cast(node)

    def COMP(self, node):
        self._gen(node.children[0])
        self._gen(node.children[1])

        if node.value == '<':
            op = 'lt'
        elif node.value == '<=':
            op = 'le'
        elif node.value == '>':
            op = 'gt'
        elif node.value == '>=':
            op = 'ge'
        elif node.value == '==':
            op = 'eq'
        elif node.value == '!=':
            op = 'ne'

        tp = node.children[0].expr_type.cls.name[0].lower()
        self._write('{}_{}'.format(op, tp))

        self._cast(node)

    def BIN(self, node):
        self._gen(node.children[0])
        self._gen(node.children[1])

        if node.value == '+':
            op = 'add'
        elif node.value == '-':
            op = 'sub'
        elif node.value == '*':
            op = 'mult'
        elif node.value == '/':
            op = 'div'
        elif node.value == '%':
            op = 'mod'

        tp = node.children[0].expr_type.cls.name[0].lower()
        self._write('{}_{}'.format(op, tp))

        self._cast(node)

    def UNARY(self, node):
        self._gen(node.children[0])

        if node.value == '-':
            tp = node.children[0].expr_type.cls.name[0].lower()
            self._write('neg_{}'.format(tp))

        self._cast(node)

    def NUM(self, node):
        self._write('const_i', node.value)

        self._cast(node)

    def FLOAT(self, node):
        self._write('const_f', node.value)

        self._cast(node)

    def VAR(self, node):
        if node.sym.TYPE == Symbol.Constant:
            if node.sym.cls == symbol.BOOL:
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

        self._cast(node)
