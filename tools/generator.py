#!/usr/bin/env python3

import sys
from lexer import Lexer
from parser import Parser

class Generator:
    def __init__(self):
        self._gens = {}
        for attr in dir(self):
            if attr[0].isupper():
                self._gens[attr] = getattr(self, attr)

    def generate(self, tree, out):
        self.out = out
        self._write('module', "'test'")
        self._write('ref_module', "'io'")
        self._write('ref_method', "'write'")
        self._write('')
        self._gen(tree)

    def _write(self, *args):
        self.out.write(' '.join(str(a) for a in args) + '\n')

    def _gen(self, node):
        self._gens[node.type](node)

    def _level(self, tp, lvl):
        l = tp.level
        while l > lvl:
            l -= 1
            self._write('load_ptr', 0, tp.size(l))

    def STMTS(self, node):
        for c in node.children:
            self._gen(c)
            self._write('')

    def LET(self, node):
        tp = node.children[0].expr_type
        self._write('push', tp.var_size())

    def EXPR(self, node):
        self._gen(node.children[0])
        # self._write('pop', '4')
        self._level(node.children[0].expr_type, 0)
        self._write('call', 0)

    def ASSN(self, node):
        self._gen(node.children[1]) # value
        self._level(node.children[1].expr_type, node.level)
        self._gen(node.children[0]) # id
        self._level(node.children[0].expr_type, node.level + 1)
        self._write('store_ptr', 0, node.children[1].expr_type.size(node.level))

    def BIN(self, node):
        self._gen(node.children[0])
        self._level(node.children[0].expr_type, 0)
        self._gen(node.children[1])
        self._level(node.children[1].expr_type, 0)
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


if __name__ == '__main__':
    with open('meta/lex') as f:
        lexer = Lexer(f)
    parser = Parser(lexer)
    generator = Generator()
    root = parser.parse(sys.stdin)
    root.annotate()
    generator.generate(root, sys.stdout)
