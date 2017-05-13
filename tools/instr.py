#!/usr/bin/env python3

import heapq

HEADER = """# Fin Instruction Set"""

FORMAT = """
## `{ins.opname}`

**Opcode**: 0x{ins.opcode:x}

**Format**: `{format}`

{ins.comment}"""

class Instr:
    def __init__(self, line, alloc):
        segs = line.split(' ')
        name = segs[0].split('=')

        self.opname = name[0]
        if len(name) > 1:
            self.opcode = int(name[1])
            alloc.remove(self.opcode)
        else:
            self.opcode = alloc.next()
        self.params = [Param(param) for param in segs[1:]]
        self.comment = ''

    def format(self):
        val = self.opname
        for p in self.params:
            val += ' ' + p.format()
        return val


class Param:
    def __init__(self, val):
        segs = val.split(':')

        self.name = segs[0]
        self.type = segs[1]

    def format(self):
        return '{}:{}'.format(self.name, self.type)


class Allocator:
    def __init__(self, size):
        self.at = 0
        self.removed = []

    def next(self):
        while len(self.removed) > 0 and self.at == self.removed[0]:
            self.at += 1
            heapq.heappop(self.removed)
        val = self.at
        self.at += 1
        return val

    def remove(self, val):
        if val < self.at or val in self.removed:
            raise ValueError('already used value')
        heapq.heappush(self.removed, val)


def load(source = 'meta/instructions'):
    # available enum values
    alloc = Allocator(256)
    instrs = []

    instr = None
    with open(source) as f:
        for line in f:
            # empty line
            if line == '\n':
                continue

            # comment
            if line[0] == ' ':
                instr.comment += line.lstrip()
                continue

            instr = Instr(line[:-1], alloc)
            instrs.append(instr)

    return instrs

def main():
    instrs = load()

    print(HEADER)

    for ins in instrs:
        print(FORMAT.format(
            ins=ins,
            format=ins.format()
            ), end='')

if __name__ == '__main__':
    main()
