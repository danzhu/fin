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

        root = self.parser.parse(tokens)

        glob = symbols.load_builtins()
        syms = symbols.load_module('fin', glob)
        refs: Set[symbols.Function] = set()

        if stage == 'parse':
            root.print()
            return

        root.analyze(name, syms, refs)

        if stage == 'ast':
            root.print()
            return

        with io.StringIO() as asm:
            assembly = cast(io.StringIO, asm)

            self.generator.generate(root,
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
    parser.add_argument('-o', dest='out', metavar='<output>',
                        type=argparse.FileType('wb'), default='a.fm',
                        help='write output to <output>')
    parser.add_argument('-n', dest='name', metavar='<name>', default='main',
                        help='name of the module')
    parser.add_argument('-s', dest='stage', metavar='<stage>', default='exec',
                        choices=['lex', 'parse', 'ast', 'asm', 'exec'],
                        help='compilation stage')
    args = parser.parse_args()

    compiler = Compiler()

    try:
        compiler.compile(args.src, args.out, args.name, args.stage)
    except CompilerError as e:
        print(f'{type(e).__name__}: {e}', file=sys.stderr)
        exit(1)


if __name__ == '__main__':
    main()
