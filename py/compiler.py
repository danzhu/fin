#!/usr/bin/env python3

from typing import Iterable, cast
import argparse
import io
import os
import sys
from finc import builtin
from finc import symbols
from finc import error
from finc import generator
from finc import lexer
from finc import parse
from finc import analyzer
from asm import Assembler


class Compiler:
    def __init__(self) -> None:
        self.lexer = lexer.Lexer()
        self.parser = parse.Parser()
        self.assembler = Assembler()

        builtins = builtin.load_builtins()
        self.root = symbols.Module('', None, builtins)

        self.analyzeImport = analyzer.AnalyzeImport(self.root)
        self.analyzeDeclare = analyzer.AnalyzeDeclare(self.root)
        self.analyzeJump = analyzer.AnalyzeJump(self.root)
        self.analyzeExpr = analyzer.AnalyzeExpr(self.root)

    def load_module(self,
                    mod_name: str,
                    parent: symbols.Module) -> symbols.Module:
        # TODO: a better way to locate
        loc = os.path.dirname(os.path.realpath(__file__))
        filename = os.path.join(loc, 'ref', f'{mod_name}.fin')
        mod = symbols.Module(mod_name, parent)
        with open(filename) as src:
            tokens = self.lexer.read(src)
            ast = self.parser.parse(tokens)
            self.analyzeImport.analyze(ast, mod)
            self.analyzeDeclare.analyze(ast, mod)

        return mod

    def compile(self,
                src: Iterable[str],
                out: io.BytesIO,
                name: str,
                stage: str) -> None:
        tokens = self.lexer.read(src)

        if stage == 'lex':
            lst = list(tokens)
            for t in lst:
                print(t)

            tokens = iter(lst)

        ast = self.parser.parse(tokens)

        if stage == 'parse':
            ast.print()

        self.load_module('rt', self.root)

        mod = symbols.Module(name, self.root)
        self.analyzeImport.analyze(ast, mod)
        self.analyzeDeclare.analyze(ast, mod)
        self.analyzeJump.analyze(ast, mod)
        self.analyzeExpr.analyze(ast, mod)

        if stage == 'ast':
            ast.print()

        with io.StringIO() as asm:
            assembly = cast(io.StringIO, asm)

            generator.Generator(ast, mod, cast(io.TextIOBase, assembly))

            if stage == 'asm':
                print(assembly.getvalue())

            assembly.seek(0)
            self.assembler.assemble(assembly, out)


def main() -> None:
    parser = argparse.ArgumentParser(description='Fin compiler.')
    parser.add_argument('src', type=argparse.FileType(), metavar='input',
                        help='source file')
    parser.add_argument('-o', '--out', dest='out', metavar='<output>',
                        type=argparse.FileType('wb'), default='a.fm',
                        help='write output to <output>')
    parser.add_argument('-n', '--name', dest='name', metavar='<name>',
                        default='main',
                        help='name of the module')
    parser.add_argument('-s', '--stage', dest='stage', metavar='<stage>',
                        default='exec',
                        choices=['lex', 'parse', 'ast', 'asm', 'exec'],
                        help='compilation stage')
    parser.add_argument('-d', '--debug', dest='debug', action='store_true',
                        help='enable debug information')
    args = parser.parse_args()

    compiler = Compiler()

    if args.debug:
        # don't catch any exceptions
        compiler.compile(args.src, args.out, args.name, args.stage)
        return

    try:
        compiler.compile(args.src, args.out, args.name, args.stage)
    except error.CompilerError as e:
        print(f'{type(e).__name__}: {e}', file=sys.stderr)
        exit(1)


if __name__ == '__main__':
    main()
