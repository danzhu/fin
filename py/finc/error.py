from .tokens import Token


class CompilerError(Exception):
    def __init__(self, msg: str, token: Token) -> None:
        super().__init__(msg)
        self.token = token

    def __str__(self) -> str:
        val = super().__str__()
        if self.token is not None:
            val += f'\n  at line {self.token.line},' \
                + ' column {self.token.column}:'

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
    pass
