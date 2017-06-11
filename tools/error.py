class CompilerError(Exception):
    def __init__(self, msg, token):
        super().__init__(msg)
        self.token = token

    def __str__(self):
        val = super().__str__()
        if self.token is not None:
            val += '\n  at line {}, column {}:'.format(
                    self.token.line,
                    self.token.column)
            val += '\n\n    ' + self.token.src
            val += '    ' + ' ' * (self.token.column - 1) + '^' * len(self.token.value)

        return val


class LexerError(CompilerError):
    pass


class ParserError(CompilerError):
    pass


class AnalyzerError(CompilerError):
    pass
