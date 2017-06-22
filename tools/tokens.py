class Token:
    def __init__(self,
                 tp: str,
                 src: str,
                 line: int,
                 col: int = 0,
                 val: str = None,
                 var: str = None) -> None:
        self.type = tp
        self.src = src
        self.line = line
        self.column = col
        self.value = val
        self.variant = var

    def __str__(self) -> str:
        s = self.type
        if self.variant:
            s += ' [' + self.variant + ']'
        if self.value:
            s += ' ' + self.value
        return s
