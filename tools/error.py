class CompilerError(Exception):
    def __init__(self, msg, ln, col, src):
        super().__init__(msg)
        self.line = ln
        self.column = col
        self.src = src

    def __str__(self):
        val = super().__str__()
        if self.line >= 0:
            val += '\n  at line {}, column {}:'.format(
                    self.line,
                    self.column)
            val += '\n\n    ' + self.src
            val += '    ' + ' ' * (self.column - 1) + '^'

        return val


class LexerError(CompilerError):
    pass


class ParserError(CompilerError):
    pass


class AnalyzerError(CompilerError):
    pass
