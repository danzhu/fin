from . import ast
from . import tokens
from . import symbols
from . import instr


class CompilerError(Exception):
    def __init__(self,
                 msg: str,
                 start: 'tokens.Token',
                 end: 'tokens.Token') -> None:
        Exception.__init__(self, msg)

        self.start = start
        self.end = end
        self.line = self.start.line
        self.column = self.start.column

    def detail(self) -> str:
        val = Exception.__str__(self)

        val += f'\n  at line {self.line},' \
            + f' column {self.column}:'

        line = self.start.src.lstrip()
        indent = len(self.start.src) - len(line)
        val += f'\n\n    {line}'
        val += '    ' + ' ' * (self.column - 1 - indent)

        # display error marker to end token only if on the same line
        if self.start.line == self.end.line:
            val += '^' * (self.end.column +
                          len(self.end.value or ' ') -
                          self.column)
        else:
            val += '^' * len(self.start.value)

        return val


class LexerError(CompilerError):
    def __init__(self, msg: str, tok: 'tokens.Token') -> None:
        CompilerError.__init__(self, msg, tok, tok)


class ParserError(CompilerError):
    def __init__(self, msg: str, tok: 'tokens.Token') -> None:
        CompilerError.__init__(self, msg, tok, tok)


class AnalyzerError(CompilerError):
    def __init__(self,
                 msg: str,
                 node: 'ast.Node',
                 sym: 'symbols.Symbol' = None) -> None:
        # TODO: use symbol declaration location
        CompilerError.__init__(self, msg, node.start_token, node.end_token)

        self.node = node
        self.symbol = sym


class SymbolError(Exception):
    def __init__(self, msg: str, sym: 'symbols.Symbol') -> None:
        Exception.__init__(self, msg)

        self.symbol = sym


class AssemblerError(Exception):
    def __init__(self, msg: str, ins: 'instr.Instr') -> None:
        Exception.__init__(self, msg)
