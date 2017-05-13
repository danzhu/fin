#!/usr/bin/env python3

import sys
from lexer import Lexer
from parse import Parser

class Generator:
    def __init__(self):
        self._gens = {}
        for attr in dir(self):
            if attr[0].isupper():
                self._gens[attr] = getattr(self, attr)

        self._labels = {}

    def generate(self, tree, out):
        self.out = out
        self._gen(tree)

    def _write(self, *args):
        self.out.write(' '.join(str(a) for a in args) + '\n')

    def _gen(self, node, level=None):
        self._gens[node.type](node)
        if level is not None:
            self._level(node.expr_type, level)

    def _level(self, tp, lvl):
        l = tp.level
        while l > lvl:
            l -= 1
            self._write('load_ptr', 0, tp.size(l))

    def _label(self, name):
        count = self._labels[name] if name in self._labels else 0
        self._labels[name] = count + 1
        return '{}_{}'.format(name, count)

    def FILE(self, node):
        for c in node.children:
            self._gen(c)
            self._write('')

    def IMPORT(self, node):
        # TODO
        pass

    def STMTS(self, node):
        for c in node.children:
            self._gen(c)
            self._write('')

    def LET(self, node):
        tp = node.children[1].expr_type
        self._write('push', tp.var_size())

    def IF(self, node):
        els = self._label('ELSE')
        end = self._label('END_IF')
        has_else = len(node.children[2].children) > 0

        self._gen(node.children[0], 0) # comp
        self._write('br_false', els if has_else else end)
        self._gen(node.children[1])
        if has_else:
            self._write('br', end)
            self._write(els + ':')
            self._gen(node.children[2])
        self._write(end + ':')

    def WHILE(self, node):
        start = self._label('WHILE')
        cond = self._label('TEST')

        self._write('br', cond)
        self._write(start + ':')
        self._gen(node.children[1])
        self._write(cond + ':')
        self._gen(node.children[0], 0) # comp
        self._write('br_true', start)

    def EXPR(self, node):
        self._gen(node.children[0], 0)
        self._write('pop', node.children[0].expr_type.size())

    def ASSN(self, node):
        self._gen(node.children[1], node.level) # value
        self._gen(node.children[0], node.level + 1) # id
        self._write('store_ptr', 0, node.children[1].expr_type.size(node.level))

    def CALL(self, node):
        for c in node.children[1:]:
            self._gen(c, 0)
        self._write('call', str(node.fn), node.arg_size)

    def COMP(self, node):
        self._gen(node.children[0], 0)
        self._gen(node.children[1], 0)
        # TODO: use actual type
        self._write(node.value.lower() + '_i')

    def BIN(self, node):
        self._gen(node.children[0], 0)
        self._gen(node.children[1], 0)
        # TODO: use actual type
        if node.value == 'PLUS':
            self._write('add_i')
        elif node.value == 'MINUS':
            self._write('sub_i')
        elif node.value == 'MULT':
            self._write('mult_i')
        elif node.value == 'DIV':
            self._write('div_i')

    def NUM(self, node):
        self._write('const_i', node.value)

    def ID(self, node):
        offset = node.id.offset
        self._write('addr_frame', offset)
