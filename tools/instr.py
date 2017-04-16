#!/usr/bin/env python3

import struct

ENC = {
        'i8':  'b',
        'u8':  'B',
        'i16': 'h',
        'u16': 'H',
        'i32': 'i',
        'u32': 'I'
        }

class Instr:
    def __init__(self, line, binary):
        segs = line.split(' ')

        self.opcode = segs[0]
        self.binary = binary
        self.params = [Param(param) for param in segs[1:]]
        # self.size   = sum([param.size for param in self.params])

    def encode(self):
        return Bytes(encode('B', self.binary))


class Param:
    def __init__(self, val):
        segs = val.split(':')

        self.name = segs[0]
        self.type = segs[1]
        # self.size = SIZE[self.type]

    def encode(self, src):
        if self.type == 's':
            return Bytes(encode('H', len(src)) + src.encode())
        elif src[0].isalpha():
            return Label(ENC[self.type], src)
        else:
            return Bytes(encode(ENC[self.type], int(src, 0)))


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


def encode(fmt, val):
    return struct.pack('<' + fmt, val)

def load(fmt = 'tools/instrs'):
    instrs = []

    with open(fmt) as f:
        for line in f:
            instr = Instr(line[:-1], len(instrs))
            instrs.append(instr)

    return instrs
