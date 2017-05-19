#!/usr/bin/env python3

import sys
import string
from enum import Enum

class State:
    def __init__(self, name):
        self.name = name
        self.transitions = {}

        self.accept = self.name[0].isupper()


class Token:
    def __init__(self, tp, line, col, val = None, var = None):
        self.type = tp
        self.line = line
        self.column = col
        self.value = val
        self.variant = var

    def __str__(self):
        s = self.type
        if self.variant:
            s += ' [' + self.variant + ']'
        if self.value:
            s += ' ' + self.value
        return s


class Lexer:
    def __init__(self, syn):
        self.states = {}
        self.types = {}
        self.keywords = {}

        for line in syn:
            segs = line[:-1].split(' ')
            if segs[0] == '>':
                start = self._state(segs[1])
                trans = self._expand(segs[2])
                end = self._state(segs[3])
                for c in trans:
                    start.transitions[c] = end
            elif segs[0] == 'type':
                self.types[segs[1]] = segs[2]
            elif segs[0] == 'keyword':
                self.keywords[segs[1]] = segs[2]

        self.start = self.states['start']

    def _expand(self, trans):
        return trans.replace('[ALPHA]', string.ascii_letters) \
                .replace('[NUM]', string.digits) \
                .replace('[SPACE]', string.whitespace) \
                .replace('[LF]', '\n') \
                .replace('[ANY]', ''.join(map(chr, range(128))))

    def _state(self, name):
        if name not in self.states:
            self.states[name] = State(name)
        return self.states[name]

    def read(self, src):
        ind_amount = 0
        indent = 0
        ln = 0
        prevEmpty = False
        # TODO: line continuation
        for line in src:
            ln += 1

            stripped = line.strip()

            if len(stripped) == 0:
                prevEmpty = True
                continue

            if stripped[0] == '#':
                continue

            new_indent = len(line) - len(line.lstrip())

            if ind_amount == 0 and new_indent > 0:
                ind_amount = new_indent

            if new_indent > indent:
                if (new_indent - indent) % ind_amount != 0:
                    raise Exception('wrong indent')
                for i in range((new_indent - indent) // ind_amount):
                    yield Token('INDENT', ln, 0)

            elif new_indent < indent:
                if (indent - new_indent) % ind_amount != 0:
                    raise Exception('wrong dedent')

                for i in range((indent - new_indent) // ind_amount):
                    yield Token('DEDENT', ln, 0)
                    if prevEmpty:
                        yield Token('EOL', ln, 0)

            indent = new_indent
            prevEmpty = False

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
                    var = None
                elif state.name in self.types:
                    tp = self.types[state.name]
                    var = state.name
                else:
                    tp = state.name
                    var = tp

                yield Token(tp, ln, start + 1, val, var)

                start = end
                state = self.start

            yield Token('EOL', ln, len(line) + 1, '\n')

        if ind_amount > 0:
            for i in range(indent // ind_amount):
                yield Token('DEDENT', ln, 0)
                yield Token('EOL', ln, 0)

        yield Token('EOF', ln, 0)
