from typing import Dict, Iterable
import string
import os
from .error import LexerError
from .tokens import Token


class State:
    def __init__(self, name: str) -> None:
        self.name = name
        self.transitions: Dict[str, State] = {}

        self.accept = self.name[0].isupper()


class Lexer:
    def __init__(self) -> None:
        self.states: Dict[str, State] = {}
        self.types: Dict[str, str] = {}
        self.keywords: Dict[str, str] = {}

        loc = os.path.dirname(os.path.realpath(__file__))
        source = os.path.join(loc, 'lex')
        with open(source) as syn:
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

        self.ind_amount: int = None

    def _expand(self, trans: str) -> str:
        return trans.replace('[ALPHA]', string.ascii_letters) \
            .replace('[NUM]', string.digits) \
            .replace('[SPACE]', string.whitespace) \
            .replace('[LF]', '\n') \
            .replace('[ANY]', ''.join(map(chr, range(128))))

    def _state(self, name: str) -> State:
        if name not in self.states:
            self.states[name] = State(name)
        return self.states[name]

    def read(self, src: Iterable[str]) -> Iterable[Token]:
        self.ind_amount = None
        indent = 0
        ln = 0
        prevEmpty = False

        # TODO: line continuation
        line = ''
        for line in src:
            ln += 1

            stripped = line.lstrip()

            if len(stripped) == 0:
                prevEmpty = True
                continue

            if stripped[0] == '#':
                continue

            new_indent = len(line) - len(stripped)

            if self.ind_amount is None and new_indent > 0:
                self.ind_amount = new_indent

            if new_indent > indent:
                if (new_indent - indent) % self.ind_amount != 0:
                    raise LexerError('wrong indent',
                                     Token('INDENT', line, ln, new_indent))

                for _ in range((new_indent - indent) // self.ind_amount):
                    yield Token('INDENT', line, ln)

            elif new_indent < indent:
                if (indent - new_indent) % self.ind_amount != 0:
                    raise LexerError('wrong dedent',
                                     Token('DEDENT', line, ln, new_indent))

                # end all blocks except the last one
                for _ in range((indent - new_indent) // self.ind_amount - 1):
                    yield Token('DEDENT', line, ln)
                    yield Token('EOL', line, ln)

                # also end the last block if followed by an empty line
                yield Token('DEDENT', line, ln)
                if prevEmpty:
                    yield Token('EOL', line, ln)

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

                if state == self.start:
                    raise LexerError(f"invalid character '{c}'",
                                     Token(state.name, line, ln, start + 1, c))

                val = line[start:end]

                if not state.accept:
                    raise LexerError(
                        f"invalid token '{val}'",
                        Token(state.name, line, ln, start + 1, val))

                if val in self.keywords:
                    tp = self.keywords[val]
                    var = None
                elif state.name in self.types:
                    tp = self.types[state.name]
                    var = state.name
                else:
                    tp = state.name
                    var = tp

                yield Token(tp, line, ln, start + 1, val, var)

                start = end
                state = self.start

            # since \n is part of line, len(line) is exactly the column of EOL
            yield Token('EOL', line, ln, len(line), '\n')

        if self.ind_amount > 0:
            for _ in range(indent // self.ind_amount):
                yield Token('DEDENT', line, ln)
                yield Token('EOL', line, ln)

        yield Token('EOF', line, ln)
