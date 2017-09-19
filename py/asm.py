#!/usr/bin/env python3

from typing import List, Iterable, Dict, Any, DefaultDict, Iterator
from collections import defaultdict
import io
import argparse
import struct
import instrs
from finc import builtin  # FIXME: circular import workaround
from finc import error
from finc import lexer
from finc import tokens
from finc import instr


BRANCH_SIZE = 4


class RefTable:
    def __init__(self) -> None:
        self.refs: Dict[str, int] = {}

    def __getitem__(self, key: str) -> int:
        return self.refs[key]

    def add(self, value: str) -> None:
        self.refs[value] = len(self.refs)


class Chunk:
    def resolve(self,
                loc: int,
                syms: Dict[str, int],
                refs: Dict[str, RefTable]) -> int:
        raise NotImplementedError()

    def write(self, out: io.BytesIO, syms: Dict[str, int]) -> None:
        raise NotImplementedError()


class Bytes(Chunk):
    def __init__(self, val: bytes) -> None:
        self.value = val

    def resolve(self,
                loc: int,
                syms: Dict[str, int],
                refs: Dict[str, RefTable]) -> int:
        return len(self.value)

    def write(self, out: io.BytesIO, syms: Dict[str, int]) -> None:
        out.write(self.value)


class Label(Chunk):
    def __init__(self, label: str) -> None:
        self.label = label

    def resolve(self,
                loc: int,
                syms: Dict[str, int],
                refs: Dict[str, RefTable]) -> int:
        syms[self.label] = loc
        return 0

    def write(self, out: io.BytesIO, syms: Dict[str, int]) -> None:
        pass


class Branch(Chunk):
    def __init__(self, label: str) -> None:
        self.label = label

        self.location: int = None

    def resolve(self,
                loc: int,
                syms: Dict[str, int],
                refs: Dict[str, RefTable]) -> int:
        self.location = loc
        return BRANCH_SIZE

    def write(self, out: io.BytesIO, syms: Dict[str, int]) -> None:
        value = syms[self.label] - (self.location + BRANCH_SIZE)
        out.write(encode(value, BRANCH_SIZE))


class Reference(Chunk):
    def __init__(self, tp: str, ref: str) -> None:
        self.type = tp
        self.ref = ref

        self.value: bytes = None

    def resolve(self,
                loc: int,
                syms: Dict[str, int],
                refs: Dict[str, RefTable]) -> int:
        self.value = encode(refs[self.type][self.ref])
        return len(self.value)

    def write(self, out: io.BytesIO, syms: Dict[str, int]) -> None:
        out.write(self.value)


class Assembler:
    def __init__(self) -> None:
        self.instrs = {ins.opname: ins for ins in instrs.load()}

        self.chunks: List[Chunk] = None
        self.references: DefaultDict[str, RefTable] = None
        self.functions: RefTable = None
        self.types: RefTable = None
        self.members: RefTable = None

        self.lib: str = None
        self.ref_lib: str = None
        self.type: str = None

    def assemble(self,
                 src: Iterable[instr.Instr],
                 out: io.BytesIO) -> None:
        self.chunks = []
        self.references = defaultdict(RefTable)
        self.functions = RefTable()
        self.types = RefTable()
        self.members = RefTable()

        # shebang
        self.chunks.append(Bytes(b'#!/usr/bin/env fin\n'))

        for ins in src:
            self.write(ins)

        syms: Dict[str, int] = {}
        location = 0

        self.references['function'] = self.functions
        self.references['type'] = self.types
        self.references['member'] = self.members

        # two-pass to resolve labels and references
        for chunk in self.chunks:
            size = chunk.resolve(location, syms, self.references)
            location += size

        for chunk in self.chunks:
            chunk.write(out, syms)

    def write(self, instruction: instr.Instr) -> None:
        if len(instruction.tokens) == 0:
            return

        opname = instruction.tokens[0]
        args = instruction.tokens[1:]

        # comment
        if opname[0] == '#':
            return

        # pseudo-label resolution
        if opname[0] == '!':
            tp = opname[1:]
            self.references[tp].add(args[0])
            return

        # label
        if opname[-1] == ':':
            if len(args) != 0:
                raise error.AssemblerError(
                    'labels need to be on their own lines',
                    instruction)

            self.chunks.append(Label(opname[:-1]))
            return

        if opname not in self.instrs:
            raise error.AssemblerError(
                f"no instruction '{opname}' defined",
                instruction)

        ins = self.instrs[opname]
        self.chunks.append(Bytes(pack('B', ins.opcode)))

        if len(args) != len(ins.params):
            raise error.AssemblerError(
                'incorrect number of arguments for' +
                f'\n  {ins}' +
                f'\n  expected {len(ins.params)}, got {len(args)}',
                instruction)

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
            chunk: Chunk
            if param.type == 'int':
                chunk = Bytes(encode(int(arg, 0)))

            elif param.type == 'str':
                if arg[0] != "'" or arg[-1] != "'":
                    raise error.AssemblerError(
                        'expected quotes around string',
                        instruction)

                val = get_name(arg)
                chunk = Bytes(encode(len(val)) + val.encode())

            elif param.type == 'fn':
                chunk = Reference('function', arg)

            elif param.type == 'tp':
                chunk = Reference('type', arg)

            elif param.type == 'mem':
                chunk = Reference('member', arg)

            elif param.type in ['sz', 'ctr', 'off']:
                chunk = Bytes(encode(self.references[param.type][arg]))

            elif param.type == 'i':
                chunk = Bytes(pack('i', int(arg, 0)))

            elif param.type == 'f':
                chunk = Bytes(pack('f', float(arg)))

            elif param.type == 'tar':
                if not arg[0].isalpha():
                    raise error.AssemblerError(
                        'branch target not a label',
                        instruction)

                chunk = Branch(arg)

            self.chunks.append(chunk)


def pack(fmt: str, val: Any) -> bytes:
    return struct.pack('<' + fmt, val)


def encode(val: int, size: int = None) -> bytes:
    enc: List[int] = []

    if val < 0:
        val = ~val
        sign = 0b01000000
    else:
        sign = 0b00000000

    enc.append(val & 0b00111111 | sign)
    val >>= 6

    while val:
        enc.append(val & 0b01111111 | 0b10000000)
        val >>= 7

    if size is not None:
        if len(enc) > size:
            # TODO: use AssemblerError
            raise ValueError('value out of range')

        while len(enc) < size:
            enc.append(0b10000000)

    return bytes(reversed(enc))


def get_name(val: str) -> str:
    return val[1:-1]


def lex(src: Iterable[str]) -> Iterator[instr.Instr]:
    lx = lexer.Lexer('asm')
    lx.disable_indent = True

    segs: List[tokens.Token] = []
    for token in lx.read(src):
        if token.type == 'EOF':
            break

        if token.type == 'EOL':
            # TODO: line number & source
            # TODO: indent?
            yield instr.Instr([t.value for t in segs],
                              indent=0)
            segs = []
        else:
            segs.append(token)


def main() -> None:
    parser = argparse.ArgumentParser(description='Fin assembler.')
    parser.add_argument('src', type=argparse.FileType(), metavar='input',
                        help='assembly source file')
    parser.add_argument('-o', dest='out', metavar='<output>',
                        type=argparse.FileType('wb'), default='a.fm',
                        help='write assembler output to <output>')
    args = parser.parse_args()

    asm = Assembler()
    tks = lex(args.src)
    asm.assemble(tks, args.out)


if __name__ == '__main__':
    main()
