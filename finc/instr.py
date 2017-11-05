import typing


class Instr:
    def __init__(self,
                 tokens: typing.Sequence[str],
                 indent: int) -> None:
        self.tokens = tokens
        self.indent = indent

    def __str__(self) -> str:
        return '  ' * self.indent + ' '.join(self.tokens)
