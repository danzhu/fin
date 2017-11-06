FINC = ./compiler.py

.PHONY: all run clean

all: test.bc

run: test.bc
	lli test.bc

clean:
	${RM} test.ll *.bc

test.bc: test.ll main.ll
	llvm-link $^ -o $@

%.ll: %.fin
	${FINC} $< -o $@ -d
