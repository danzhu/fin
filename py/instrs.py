#!/usr/bin/env python3

from typing import List
import heapq
import os

HEADER = """# Fin Instruction Set"""

FORMAT = """
## `{ins.opname}`

**Opcode**: 0x{ins.opcode:x}

**Format**: `{ins}`

{ins.comment}"""


class Instr:
    def __init__(self, line: str, alloc: 'Allocator') -> None:
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

    def __str__(self) -> str:
        val = self.opname
        for p in self.params:
            val += f' {p}'
        return val


class Param:
    def __init__(self, val: str) -> None:
        segs = val.split(':')

        self.name = segs[0]
        self.type = segs[1]

    def __str__(self) -> str:
        return f'{self.name}:{self.type}'


class Allocator:
    def __init__(self, size: int) -> None:
        self.at = 0
        self.size = size
        self.removed: List[int] = []

    def next(self) -> int:
        while len(self.removed) > 0 and self.at == self.removed[0]:
            self.at += 1
            heapq.heappop(self.removed)

        if self.at >= self.size:
            raise ValueError('exceeding maximum instruction count')

        val = self.at
        self.at += 1
        return val

    def remove(self, val: int) -> None:
        if val < self.at or val in self.removed:
            raise ValueError('already used value')
        heapq.heappush(self.removed, val)


def load() -> List[Instr]:
    loc = os.path.dirname(os.path.realpath(__file__))
    source = os.path.join(loc, 'instructions')

    # available enum values
    alloc = Allocator(256)
    instrs = []

    instr: Instr = None
    with open(source) as f:
        for line in f:
            # empty line
            if line == '\n':
                continue

            # comment
            if line[0] == ' ' and instr is not None:
                instr.comment += line.lstrip()
                continue

            instr = Instr(line[:-1], alloc)
            instrs.append(instr)

    return instrs


def main() -> None:
    instrs = load()

    print(HEADER)

    for ins in instrs:
        print(FORMAT.format(ins=ins), end='')


if __name__ == '__main__':
    main()
