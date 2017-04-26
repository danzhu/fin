#!/usr/bin/env python3

import sys
import string
from collections import namedtuple
from enum import Enum

Token = namedtuple('Token', 'type value')

class State:
    def __init__(self, name):
        self.name = name
        self.transitions = {}

        self.accept = self.name[0].isupper()


class Lexer:
    def __init__(self, syn):
        self.states = {}
        self.types = {}
        self.keywords = {}

        for line in syn:
            segs = line[:-1].split(' ')
            if segs[0] == '>':
                start = self.state(segs[1])
                trans = self.expand(segs[2])
                end = self.state(segs[3])
                for c in trans:
                    start.transitions[c] = end
            elif segs[0] == 'type':
                self.types[segs[1]] = segs[2]
            elif segs[0] == 'keyword':
                self.keywords[segs[1]] = segs[2]

        self.start = self.states['start']

    def expand(self, trans):
        return trans.replace('[ALPHA]', string.ascii_letters) \
                .replace('[NUM]', string.digits) \
                .replace('[SPACE]', string.whitespace) \
                .replace('[LF]', '\n') \
                .replace('[ANY]', ''.join(map(chr, range(128))))

    def state(self, name):
        if name not in self.states:
            self.states[name] = State(name)
        return self.states[name]

    def read(self, src):
        ind_amount = 0
        indent = 0
        for line in src:
            if len(line.strip()) == 0:
                continue

            new_indent = len(line) - len(line.lstrip())

            if ind_amount == 0 and new_indent > 0:
                ind_amount = new_indent

            if new_indent > indent:
                if (new_indent - indent) % ind_amount != 0:
                    raise Exception('wrong indent')
                for i in range((new_indent - indent) // ind_amount):
                    yield Token('INDENT', None)

            elif new_indent < indent:
                if (indent - new_indent) % ind_amount != 0:
                    raise Exception('wrong dedent')
                for i in range((indent - new_indent) // ind_amount):
                    yield Token('DEDENT', None)

            indent = new_indent

            start = 0
            end = 0
            state = self.start
            while True:
                c = line[end]

                if c in state.transitions:
                    state = state.transitions[c]
                    end += 1

                    if end == len(line):
                        break

                    if state == self.start:
                        start = end

                    continue

                if not state.accept:
                    raise Exception('invalid token at {}'.format(state.name))

                val = line[start:end]

                if val in self.keywords:
                    tp = self.keywords[val]
                elif state.name in self.types:
                    tp = self.types[state.name]
                else:
                    tp = state.name

                yield Token(tp, val)

                start = end
                state = self.start

            yield Token('EOL', None)

        for i in range(indent // ind_amount):
            yield Token('DEDENT', None)

        yield Token('EOF', None)


if __name__ == '__main__':
    with open('meta/lex') as f:
        lexer = Lexer(f)

    for t in lexer.read(sys.stdin):
        print(t)
