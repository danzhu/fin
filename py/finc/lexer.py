from typing import Dict, Iterable, Iterator
import string
from pathlib import Path
from .error import LexerError
from .tokens import Token


class State:
    def __init__(self, name: str) -> None:
        self.name = name
        self.transitions: Dict[str, State] = {}

        self.accept = self.name[0].isupper()


class Lexer:
    def __init__(self, grammar: str) -> None:
        self.states: Dict[str, State] = {}
        self.types: Dict[str, str] = {}
        self.keywords: Dict[str, str] = {}
        self.disable_indent = False

        source = Path(__file__).parent.parent / 'lex' / f'{grammar}.lex'
        with source.open() as syn:
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
                else:
                    assert False, f'unknown lexer instruction {segs[0]}'

        self._start = self.states['start']

        self._ind_amount: int = None
        self._indent: int = None
        self._ln: int = None
        self._prev_empty = False
        self._eol_token: Token = None

    def _expand(self, trans: str) -> str:
        return trans \
            .replace('[ALPHA]', string.ascii_letters) \
            .replace('[NUM]', string.digits) \
            .replace('[SPACE]', string.whitespace) \
            .replace('[LF]', '\n') \
            .replace('[ANY]', ''.join(map(chr, range(128))))

    def _state(self, name: str) -> State:
        if name not in self.states:
            self.states[name] = State(name)

        return self.states[name]

    def _startline(self, line: str) -> Iterator[Token]:
        new_indent = len(line) - len(line.lstrip())

        if self._ind_amount is None and new_indent > 0:
            self._ind_amount = new_indent

        if self.disable_indent or new_indent == self._indent:
            if self._eol_token is not None:
                yield self._eol_token

        elif new_indent > self._indent:
            diff = new_indent - self._indent

            if diff % self._ind_amount != 0:
                tok = Token('INDENT', line, self._ln, new_indent)
                raise LexerError('wrong indent', tok)

            for _ in range(diff // self._ind_amount):
                yield Token('INDENT', line, self._ln)

        elif new_indent < self._indent:
            assert self._eol_token is not None
            yield self._eol_token

            diff = self._indent - new_indent

            if diff % self._ind_amount != 0:
                tok = Token('DEDENT', line, self._ln, new_indent)
                raise LexerError('wrong dedent', tok)

            # end all blocks except the last one
            for _ in range(diff // self._ind_amount - 1):
                yield Token('DEDENT', line, self._ln)
                yield Token('EOL', line, self._ln)

            # also end the last block if followed by an empty line
            yield Token('DEDENT', line, self._ln)
            if self._prev_empty:
                yield Token('EOL', line, self._ln)

        self._indent = new_indent
        self._prev_empty = False

    def _readline(self, line) -> Iterator[Token]:
        # TODO: line continuation
        self._ln += 1

        stripped = line.lstrip()

        if len(stripped) == 0:
            self._prev_empty = True
            return

        # TODO: hacks
        if stripped[0] == '#':
            return

        yield from self._startline(line)

        start = 0
        end = 0
        state = self._start
        while True:
            c = line[end]

            if c in state.transitions:
                state = state.transitions[c]
                end += 1

                if end == len(line):
                    break

                if state == self._start:
                    start = end

                continue

            if state == self._start:
                tok = Token(state.name, line, self._ln, start + 1, c)
                raise LexerError(f"invalid character '{c}'", tok)

            val = line[start:end]

            if not state.accept:
                tok = Token(state.name, line, self._ln, start + 1, val)
                raise LexerError(f"invalid token '{val}'", tok)

            if val in self.keywords:
                tp = self.keywords[val]
                var = None
            elif state.name in self.types:
                tp = self.types[state.name]
                var = state.name
            else:
                tp = state.name
                var = tp

            yield Token(tp, line, self._ln, start + 1, val, var)

            start = end
            state = self._start

        # since '\n' is part of line, len(line) is exactly the column of EOL
        self._eol_token = Token('EOL', line, self._ln, len(line), '\n')

    def read(self, src: Iterable[str]) -> Iterator[Token]:
        self._ind_amount = None
        self._indent = 0
        self._ln = 0
        self._prev_empty = False
        self._eol_token = None

        # if no lines, 'line' will not be unassigned
        line = ''
        for line in src:
            yield from self._readline(line)

        if self._eol_token is not None:
            yield self._eol_token

        if self._ind_amount is not None:
            for _ in range(self._indent // self._ind_amount):
                yield Token('DEDENT', line, self._ln)
                yield Token('EOL', line, self._ln)

        yield Token('EOF', line, self._ln)
