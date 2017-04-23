#!/usr/bin/env python3

import argparse
import instr

def main():
    parser = argparse.ArgumentParser(description='Fin assembler.')
    parser.add_argument('src', type=argparse.FileType(), metavar='input',
            help='assembly source file')
    parser.add_argument('-o', dest='out', metavar='<output>',
            type=argparse.FileType('w'), default='a.fm',
            help='write assembler output to <output>')
    args = parser.parse_args()

    assemble(args.src, args.out.buffer)

def assemble(src, out):
    instrs = {ins.opname: ins for ins in instr.load()}

    location = 0
    tokens = []
    table = {}

    tokens.append(instr.Bytes(b'#!/usr/bin/env fin\n'))

    for line in src:
        line = line.strip()
        if len(line) == 0:
            continue

        segs = line.split(' ')

        while len(segs) > 0 and segs[0][-1] == ':':
            table[segs[0][:-1]] = location
            segs = segs[1:]

        if len(segs) == 0 or segs[0] == '#':
            continue

        ins = instrs[segs[0]]
        token = ins.encode()
        location += token.size
        tokens.append(token)

        params = []
        for i in range(len(ins.params)):
            token = ins.params[i].encode(segs[i + 1])
            location += token.size
            params.append(token)
            tokens.append(token)

        for param in params:
            param.locate(location)

    for token in tokens:
        token.write(out, table)

if __name__ == '__main__':
    main()
