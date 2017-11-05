FINC = ./compiler.py

.PHONY: all run clean

all: test.ll

run: test.ll
	lli test.ll

clean:
	${RM} *.ll

%.ll: %.fin
	${FINC} $< -o $@ -d
