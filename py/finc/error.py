from . import ast
from . import tokens


class CompilerError(Exception):
    def __init__(self,
                 msg: str,
                 start: tokens.Token,
                 end: tokens.Token) -> None:
        super().__init__(msg)

        self.start = start
        self.end = end

    def __str__(self) -> str:
        val = super().__str__()
        if self.start is None:
            return val

        val += f'\n  at line {self.start.line},' \
            + f' column {self.start.column}:'

        line = self.start.src.lstrip()
        indent = len(self.start.src) - len(line)
        val += f'\n\n    {line}'
        val += '    ' + ' ' * (self.start.column - 1 - indent)

        # display error marker to end token only if on the same line
        if self.start.line == self.end.line:
            val += '^' * (self.end.column +
                          len(self.end.value or ' ') -
                          self.start.column)
        else:
            val += '^' * len(self.start.value)

        return val


class LexerError(CompilerError):
    def __init__(self, msg: str, tok: tokens.Token) -> None:
        super().__init__(msg, tok, tok)


class ParserError(CompilerError):
    def __init__(self, msg: str, tok: tokens.Token) -> None:
        super().__init__(msg, tok, tok)


class AnalyzerError(CompilerError):
    def __init__(self, msg: str, node: ast.Node) -> None:
        super().__init__(msg, node.start_token, node.end_token)


class AssemblerError(Exception):
    def __init__(self, msg: str, line: str, ln: int) -> None:
        super().__init__(msg)
        self.line = line
        self.line_number = ln

    def __str__(self) -> str:
        val = super().__str__()
        val += f'  at line {self.line_number}:'
        val += f'\n\n    {self.line}'
        return val
