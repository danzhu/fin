#!/usr/bin/env python3

import sys
import instr

def main():
    instrs = {ins.opcode: ins for ins in instr.load()}

    location = 0
    tokens = []
    table = {}

    for line in sys.stdin:
        line = line[:-1]
        if len(line) == 0 or line[0] == '#':
            continue

        if line[-1] == ':':
            table[line[:-1]] = location
            continue

        segs = line.split(' ')

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
        token.write(sys.stdout, table)

if __name__ == '__main__':
    main()
