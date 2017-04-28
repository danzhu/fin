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
        self._gen(tree)

    def _write(self, *args):
        self.out.write(' '.join(args) + '\n')

    def _gen(self, node):
        self._gens[node.type](node)

    def STMTS(self, node):
        for c in node.children:
            self._gen(c)

    def EXPR(self, node):
        self._gen(node.children[0])
        self._write('pop', '4')

    def BIN(self, node):
        self._gen(node.children[0])
        self._gen(node.children[1])
        if node.variant == 'PLUS':
            self._write('add_i')
        elif node.variant == 'MINUS':
            self._write('sub_i')
        elif node.variant == 'MULT':
            self._write('mult_i')
        elif node.variant == 'DIV':
            self._write('div_i')

    def NUM(self, node):
        self._write('const_i', node.value)


if __name__ == '__main__':
    with open('meta/lex') as f:
        lexer = Lexer(f)
    parser = Parser(lexer)
    generator = Generator()
    generator.generate(parser.parse(sys.stdin), sys.stdout)
