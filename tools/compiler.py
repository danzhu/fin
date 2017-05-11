#!/usr/bin/env python3

import argparse
import io
from lexer import Lexer
from parse import Parser
from generator import Generator
from asm import Assembler

class Compiler:
    def __init__(self, lex):
        with open(lex) as f:
            self.lexer = Lexer(f)
        self.parser = Parser()
        self.generator = Generator()
        self.assembler = Assembler()

    def compile(self, src, out, name):
        tokens = self.lexer.read(src)
        root = self.parser.parse(tokens)
        root.analyze()
        with io.StringIO() as assembly:
            self.generator.generate(root, assembly)
            assembly.seek(0)
            self.assembler.assemble(assembly, out.buffer, name)


def main():
    parser = argparse.ArgumentParser(description='Fin compiler.')
    parser.add_argument('src', type=argparse.FileType(), metavar='input',
            help='source file')
    parser.add_argument('-o', dest='out', metavar='<output>',
            type=argparse.FileType('w'), default='a.fm',
            help='write output to <output>')
    parser.add_argument('-n', dest='name', metavar='<name>', default='main',
            help='name of the module')
    args = parser.parse_args()

    compiler = Compiler('meta/lex')
    compiler.compile(args.src, args.out, args.name)

if __name__ == '__main__':
    main()
