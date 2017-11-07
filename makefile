FINC = ./compiler.py

SOURCES = compiler.py \
finc/analyzer.py \
finc/ast.py \
finc/builtin.py \
finc/error.py \
finc/generator.py \
finc/__init__.py \
finc/instr.py \
finc/lexer.py \
finc/parser.py \
finc/pattern.py \
finc/symbols.py \
finc/tokens.py \
finc/types.py

.PHONY: all run clean

all: test.bc

run: test.bc
	lli test.bc

clean:
	${RM} test.ll *.bc

test.bc: test.ll main.ll
	llvm-link $^ -o $@

%.ll: %.fin ${SOURCES}
	${FINC} $< -o $@
