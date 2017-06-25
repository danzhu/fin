#!/usr/bin/env python3

from typing import Set, Iterable, cast
import argparse
import io
import sys
from asm import Assembler
from finc import symbols
from finc.error import CompilerError
from finc.generator import Generator
from finc.lexer import Lexer
from finc.parse import Parser
from finc.reflect import Module


class Compiler:
    def __init__(self) -> None:
        self.lexer = Lexer()
        self.parser = Parser()
        self.generator = Generator()
        self.assembler = Assembler()

    def compile(self,
                src: Iterable[str],
                out: io.BytesIO,
                name: str,
                stage: str) -> None:
        tokens = self.lexer.read(src)

        if stage == 'lex':
            for t in tokens:
                print(t)
            return

        ast = self.parser.parse(tokens)

        if stage == 'parse':
            ast.print()
            return

        builtins = symbols.load_builtins()
        root = Module('', None, builtins)
        symbols.load_module('rt', root)

        refs: Set[symbols.Function] = set()

        mod = Module(name, root)
        ast.analyze(mod, root, refs)

        if stage == 'ast':
            ast.print()
            return

        with io.StringIO() as asm:
            assembly = cast(io.StringIO, asm)

            self.generator.generate(ast,
                                    name,
                                    refs,
                                    cast(io.TextIOBase, assembly))

            if stage == 'asm':
                print(assembly.getvalue())
                return

            assembly.seek(0)
            self.assembler.assemble(assembly, out)

            if stage == 'exec':
                return

        raise CompilerError('invalid stage', None)


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
    except CompilerError as e:
        print(f'{type(e).__name__}: {e}', file=sys.stderr)
        exit(1)


if __name__ == '__main__':
    main()
