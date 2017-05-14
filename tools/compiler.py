#!/usr/bin/env python3

import argparse
import io
from lexer import Lexer
from parse import Parser
from generator import Generator
from asm import Assembler
import data

class Compiler:
    def __init__(self, lex):
        with open(lex) as f:
            self.lexer = Lexer(f)
        self.parser = Parser()
        self.generator = Generator()
        self.assembler = Assembler()

    def compile(self, src, out, name, stage):
        tokens = self.lexer.read(src)

        if stage == 'lex':
            for t in tokens:
                print(t)
            return

        root = self.parser.parse(tokens)

        tps = data.builtin_types()
        fns = {}
        data.load_module('fin', tps, fns)

        root.analyze(tps, fns)

        if stage == 'parse':
            root.print()
            return

        with io.StringIO() as assembly:
            self.generator.generate(root, assembly)

            if stage == 'asm':
                print(assembly.getvalue())
                return

            assembly.seek(0)
            self.assembler.assemble(assembly, out.buffer, name)

            if stage == 'exec':
                return

        raise ValueError('invalid stage')


def main():
    parser = argparse.ArgumentParser(description='Fin compiler.')
    parser.add_argument('src', type=argparse.FileType(), metavar='input',
            help='source file')
    parser.add_argument('-o', dest='out', metavar='<output>',
            type=argparse.FileType('w'), default='a.fm',
            help='write output to <output>')
    parser.add_argument('-n', dest='name', metavar='<name>', default='main',
            help='name of the module')
    parser.add_argument('-s', dest='stage', metavar='<stage>', default='exec',
            choices=['lex', 'parse', 'asm', 'exec'],
            help='compilation stage')
    args = parser.parse_args()

    compiler = Compiler('meta/lex')
    compiler.compile(args.src, args.out, args.name, args.stage)

if __name__ == '__main__':
    main()
