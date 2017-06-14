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

            line = self.token.src.lstrip()
            indent = len(self.token.src) - len(line)
            val += '\n\n    ' + line
            val += '    ' + ' ' * (self.token.column - 1 - indent)
            val += '^' * len(self.token.value)

        return val


class LexerError(CompilerError):
    pass


class ParserError(CompilerError):
    pass


class AnalyzerError(CompilerError):
    pass
