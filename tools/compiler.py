#!/usr/bin/env python3

import argparse
import io
from lexer import Lexer
from parser import Parser
from generator import Generator
import asm

class Compiler:
    def __init__(self, lex):
        with open(lex) as f:
            lexer = Lexer(f)
        self.parser = Parser(lexer)
        self.generator = Generator()

    def compile(self, src, out):
        self.generator.generate(self.parser.parse(src), out)


def main():
    parser = argparse.ArgumentParser(description='Fin compiler.')
    parser.add_argument('src', type=argparse.FileType(), metavar='input',
            help='source file')
    parser.add_argument('-o', dest='out', metavar='<output>',
            type=argparse.FileType('w'), default='a.fm',
            help='write output to <output>')
    args = parser.parse_args()

    with io.StringIO() as assembly:
        compiler = Compiler('meta/lex')
        compiler.compile(args.src, assembly)

        assembly.seek(0)

        asm.assemble(assembly, args.out.buffer)

if __name__ == '__main__':
    main()
