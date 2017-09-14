from . import ast
from . import tokens


class CompilerError(Exception):
    def __init__(self, msg: str, token: tokens.Token) -> None:
        super().__init__(msg)
        self.token = token

    def __str__(self) -> str:
        val = super().__str__()
        if self.token is not None:
            val += f'\n  at line {self.token.line},' \
                + f' column {self.token.column}:'

            line = self.token.src.lstrip()
            indent = len(self.token.src) - len(line)
            val += f'\n\n    {line}'
            val += '    ' + ' ' * (self.token.column - 1 - indent)
            val += '^' * len(self.token.value or ' ')

        return val


class LexerError(CompilerError):
    pass


class ParserError(CompilerError):
    pass


class AnalyzerError(CompilerError):
    def __init__(self, msg: str, node: ast.Node) -> None:
        # TODO: print token location
        super().__init__(msg, None)


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
