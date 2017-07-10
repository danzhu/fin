#!/usr/bin/env python3

from typing import List, Iterable, Dict, Any, DefaultDict
from collections import defaultdict
import io
import argparse
import struct
import instr


class RefTable:
    def __init__(self) -> None:
        self.refs: Dict[str, int] = {}

    def __getitem__(self, key: str) -> int:
        return self.refs[key]

    def add(self, value: str) -> None:
        self.refs[value] = len(self.refs)


class Token:
    size: int

    def resolve(self, loc: int, syms: Dict[str, int]) -> None:
        raise NotImplementedError()

    def write(self,
              out: io.BytesIO,
              syms: Dict[str, int],
              refs: Dict[str, RefTable]) -> None:
        raise NotImplementedError()


class Bytes(Token):
    def __init__(self, val: bytes) -> None:
        self.value = val
        self.size = len(val)

    def resolve(self, loc: int, syms: Dict[str, int]) -> None:
        pass

    def write(self,
              out: io.BytesIO,
              syms: Dict[str, int],
              refs: Dict[str, RefTable]) -> None:
        out.write(self.value)


class Label(Token):
    def __init__(self, label: str) -> None:
        self.label = label
        self.size = 0

    def resolve(self, loc: int, syms: Dict[str, int]) -> None:
        syms[self.label] = loc

    def write(self,
              out: io.BytesIO,
              syms: Dict[str, int],
              refs: Dict[str, RefTable]) -> None:
        pass


class Branch(Token):
    def __init__(self, enc: str, label: str) -> None:
        self.enc = enc
        self.label = label
        self.size = struct.calcsize(enc)
        self.location: int = None

    def resolve(self, loc: int, syms: Dict[str, int]) -> None:
        self.location = loc

    def write(self,
              out: io.BytesIO,
              syms: Dict[str, int],
              refs: Dict[str, RefTable]) -> None:
        value = syms[self.label] - (self.location + self.size)
        out.write(encode(self.enc, value))


class Reference(Token):
    def __init__(self, tp: str, val: str) -> None:
        self.enc = 'I'
        self.type = tp
        self.value = val
        self.size = struct.calcsize(self.enc)

    def resolve(self, loc: int, syms: Dict[str, int]) -> None:
        pass

    def write(self,
              out: io.BytesIO,
              syms: Dict[str, int],
              refs: Dict[str, RefTable]) -> None:
        out.write(encode(self.enc, refs[self.type][self.value]))


class Assembler:
    def __init__(self) -> None:
        self.instrs = {ins.opname: ins for ins in instr.load()}

        self.tokens: List[Token] = None
        self.references: DefaultDict[str, RefTable] = None
        self.functions: RefTable = None
        self.types: RefTable = None
        self.members: RefTable = None

        self.lib: str = None
        self.ref_lib: str = None
        self.type: str = None

    def assemble(self, src: Iterable[str], out: io.BytesIO) -> None:
        self.tokens = []
        self.references = defaultdict(RefTable)
        self.functions = RefTable()
        self.types = RefTable()
        self.members = RefTable()

        # shebang
        self.tokens.append(Bytes(b'#!/usr/bin/env fin\n'))

        for line in src:
            line = line.split('#')[0].strip()
            if line == '':
                continue

            segs = line.split(' ')

            # labels
            while len(segs) > 0 and segs[0][-1] == ':':
                self.tokens.append(Label(segs[0][:-1]))
                segs = segs[1:]

            if len(segs) == 0:
                continue

            self.instr(segs[0], *segs[1:])

        syms: Dict[str, int] = {}
        location = 0

        self.references['function'] = self.functions
        self.references['type'] = self.types
        self.references['member'] = self.members

        # two-pass approach since labels need to be calculated first
        for token in self.tokens:
            token.resolve(location, syms)
            location += token.size

        for token in self.tokens:
            token.write(out, syms, self.references)

    def instr(self, opname: str, *args: str) -> None:
        # pseudo-label resolution
        if opname[0] == '!':
            tp = opname[1:]
            self.references[tp].add(args[0])
            return

        if opname not in self.instrs:
            raise LookupError(f"no instruction '{opname}' defined")

        ins = self.instrs[opname]
        self.tokens.append(Bytes(encode('B', ins.opcode)))

        if len(args) != len(ins.params):
            raise ValueError('incorrect number of arguments for\n' +
                             f'{ins}\n' +
                             f'expected {len(ins.params)}, got {len(args)}')

        if len(args) > 0:
            name = get_name(args[0])

            if opname == 'ref_lib':
                self.ref_lib = name

            elif opname == 'ref_fn':
                self.functions.add(f'{self.ref_lib}:{name}')

            elif opname == 'ref_type':
                self.types.add(f'{self.ref_lib}:{name}')

            elif opname == 'lib':
                self.lib = name

            elif opname == 'fn':
                self.functions.add(f'{self.lib}:{name}')
                self.references.clear()

            elif opname == 'type':
                self.type = f'{self.lib}:{name}'
                self.types.add(self.type)
                self.references.clear()

            elif opname == 'member':
                self.members.add(f'{self.type}:{name}')

        for param, arg in zip(ins.params, args):
            token: Token
            if param.type == 'str':
                if arg[0] != "'" or arg[-1] != "'":
                    raise ValueError('expected quotes around string')

                arg = arg[1:-1]
                token = Bytes(encode('H', len(arg)) + arg.encode())

            elif param.type == 'fn':
                token = Reference('function', arg)

            elif param.type == 'tp':
                token = Reference('type', arg)

            elif param.type == 'mem':
                token = Reference('member', arg)

            elif param.type in ['sz', 'ctr', 'off']:
                token = Bytes(encode('H', self.references[param.type][arg]))

            elif param.type == 'f':
                token = Bytes(encode(param.type, float(arg)))

            elif arg[0].isalpha():
                token = Branch(param.type, arg)

            else:
                token = Bytes(encode(param.type, int(arg, 0)))

            self.tokens.append(token)


def encode(fmt: str, val: Any) -> bytes:
    return struct.pack('<' + fmt, val)


def get_name(val: str) -> str:
    return val[1:-1]


def main() -> None:
    parser = argparse.ArgumentParser(description='Fin assembler.')
    parser.add_argument('src', type=argparse.FileType(), metavar='input',
                        help='assembly source file')
    parser.add_argument('-o', dest='out', metavar='<output>',
                        type=argparse.FileType('wb'), default='a.fm',
                        help='write assembler output to <output>')
    args = parser.parse_args()

    asm = Assembler()
    asm.assemble(args.src, args.out)


if __name__ == '__main__':
    main()
