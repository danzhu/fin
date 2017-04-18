CXX := g++
CXXFLAGS := -std=c++14 -Wall -Wextra -Wno-unused-parameter -MMD -g
LDFLAGS :=
LDLIBS :=

EXEC := fin
DIST := ${EXEC}.zip
TEST := test.fm
INST := ~/bin

SRCDIR := src
OBJDIR := obj
DOCDIR := doc

SOURCES := $(wildcard ${SRCDIR}/*.cc)
HEADERS := $(wildcard ${SRCDIR}/*.h)
OBJECTS := $(patsubst ${SRCDIR}/%.cc,${OBJDIR}/%.o,${SOURCES})
DEPENDS := $(patsubst ${SRCDIR}/%.cc,${OBJDIR}/%.d,${SOURCES})

.PHONY: all debug run clean doc dist install uninstall

all: ${EXEC}

debug: CXXFLAGS += -DDEBUG
debug: ${EXEC}

run: ${EXEC} ${TEST}
	./${EXEC} ${TEST}

clean:
	${RM} ${EXEC} ${DIST} ${TEST} ${OBJECTS} ${DEPENDS}

doc: $(wildcard ${DOCDIR}/*.md)

dist:
	git archive -o ${DIST} HEAD

install: ${EXEC}
	cp ${EXEC} ${INST}/

uninstall:
	${RM} ${INST}/${EXEC}

${EXEC}: ${HEADERS} ${OBJECTS}
	${CXX} ${CXXFLAGS} ${OBJECTS} -o $@ ${LDFLAGS} ${LDLIBS}

${OBJDIR}/%.o: ${SRCDIR}/%.cc | ${OBJDIR}
	${CXX} ${CXXFLAGS} -c $< -o $@

${OBJDIR}:
	mkdir $@

%.fm: %.asm tools/asm.py tools/instr.py
	tools/asm.py < $< > $@
	chmod +x $@

${SRCDIR}/opcode.h: tools/opcode.py tools/instr.py meta/instructions
	$< > $@

${DOCDIR}/instructions.md: tools/instructions.py tools/instr.py \
	meta/instructions
	$< > $@

-include ${DEPENDS}
