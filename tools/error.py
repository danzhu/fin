class CompilerError(Exception):
    def __init__(self, msg, ln, col):
        super().__init__(msg + '\n  at line {}, col {}'.format(ln, col))


class LexerError(CompilerError):
    pass


class ParserError(CompilerError):
    pass


class AnalyzerError(CompilerError):
    pass
