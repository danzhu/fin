#!/usr/bin/env python3

import struct
import heapq

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

    def encode(self):
        return Bytes(encode('B', self.opcode))

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

    def encode(self, src):
        if self.type == 's':
            if src[0] != "'" or src[-1] != "'":
                raise ValueError('missing quotes')
            src = src[1:-1]
            return Bytes(encode('H', len(src)) + src.encode())
        elif src[0].isalpha():
            return Label(self.type, src)
        else:
            return Bytes(encode(self.type, int(src, 0)))

    def format(self):
        return '{}:{}'.format(self.name, self.type)


class Bytes:
    def __init__(self, val):
        self.value = val
        self.size = len(val)

    def locate(self, loc):
        pass

    def write(self, out, table):
        out.buffer.write(self.value)


class Label:
    def __init__(self, enc, label):
        self.enc = enc
        self.label = label
        self.size = struct.calcsize(enc)

    def locate(self, loc):
        self.loc = loc

    def write(self, out, table):
        value = table[self.label] - self.loc
        out.buffer.write(encode(self.enc, value))


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


def encode(fmt, val):
    return struct.pack('<' + fmt, val)

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
