#!/usr/bin/env python3

import argparse
import struct
import instr

class Bytes:
    def __init__(self, val):
        self.value = val
        self.size = len(val)

    def resolve(self, loc, syms):
        pass

    def write(self, out, syms, refs):
        out.write(self.value)


class Label:
    def __init__(self, label):
        self.label = label
        self.size = 0

    def resolve(self, loc, syms):
        syms[self.label] = loc

    def write(self, out, syms, refs):
        pass


class Branch:
    def __init__(self, enc, label):
        self.enc = enc
        self.label = label
        self.size = struct.calcsize(enc)
        self.location = None

    def resolve(self, loc, syms):
        self.location = loc

    def write(self, out, syms, refs):
        value = syms[self.label] - (self.location + self.size)
        out.write(encode(self.enc, value))


class Reference:
    def __init__(self, val):
        self.enc = 'I'
        self.value = val
        self.size = struct.calcsize(self.enc)

    def resolve(self, loc, syms):
        pass

    def write(self, out, syms, refs):
        out.write(encode(self.enc, refs[self.value]))


class Assembler:
    def __init__(self):
        self.instrs = {ins.opname: ins for ins in instr.load()}
        self.tokens = None
        self.references = None
        self.ref_module = None
        self.module = None

    def assemble(self, src, out):
        self.tokens = []
        self.references = []

        # shebang
        self.tokens.append(Bytes(b'#!/usr/bin/env fin\n'))

        for line in src:
            line = line.strip()
            if line == '':
                continue

            segs = line.split(' ')

            while len(segs) > 0 and segs[0][-1] == ':':
                self.tokens.append(Label(segs[0][:-1]))
                segs = segs[1:]

            if segs == [] or segs[0] == '#':
                continue

            self.instr(segs[0], *segs[1:])

        refs = {ref: i for i, ref in enumerate(self.references)}

        syms = {}
        location = 0

        # two-pass approach since labels need to be calculated first
        for token in self.tokens:
            token.resolve(location, syms)
            location += token.size

        for token in self.tokens:
            token.write(out, syms, refs)

    def instr(self, opname, *args):
        ins = self.instrs[opname]
        token = Bytes(encode('B', ins.opcode))
        self.tokens.append(token)

        if len(args) != len(ins.params):
            raise ValueError('incorrect number of arguments')

        if opname == 'ref_module':
            self.ref_module = args[0]

        elif opname == 'ref_function':
            self.references.append('{}:{}'.format(self.ref_module, args[0]))

        elif opname == 'module':
            self.module = args[0]

        elif opname == 'function':
            self.references.append('{}:{}'.format(self.module, args[0]))

        for param, arg in zip(ins.params, args):
            if param.type == 's':
                token = Bytes(encode('H', len(arg)) + arg.encode())

            elif param.type == 'r':
                token = Reference(arg)

            elif arg[0].isalpha():
                token = Branch(param.type, arg)

            elif param.type == 'f':
                token = Bytes(encode(param.type, float(arg)))

            else:
                token = Bytes(encode(param.type, int(arg, 0)))

            self.tokens.append(token)


def encode(fmt, val):
    return struct.pack('<' + fmt, val)

def main():
    parser = argparse.ArgumentParser(description='Fin assembler.')
    parser.add_argument('src', type=argparse.FileType(), metavar='input',
                        help='assembly source file')
    parser.add_argument('-o', dest='out', metavar='<output>',
                        type=argparse.FileType('w'), default='a.fm',
                        help='write assembler output to <output>')
    args = parser.parse_args()

    asm = Assembler()
    asm.assemble(args.src, args.out.buffer)

if __name__ == '__main__':
    main()
