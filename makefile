CXX := g++
CXXFLAGS := -std=c++14 -Wall -Wextra -Wno-unused-parameter -MMD -g
LDFLAGS :=

EXEC := fin
DIST := ${EXEC}.zip
TEST := test.fin

SRCDIR := src
OBJDIR := obj

SOURCES := $(wildcard ${SRCDIR}/*.cc)
OBJECTS := $(patsubst ${SRCDIR}/%.cc,${OBJDIR}/%.o,${SOURCES})
DEPENDS := $(patsubst ${SRCDIR}/%.cc,${OBJDIR}/%.d,${SOURCES})

.PHONY: all debug dist clean run

all: ${EXEC}

debug: CXXFLAGS += -DDEBUG
debug: ${EXEC}

dist:
	git archive -o ${DIST} HEAD

clean:
	${RM} ${EXEC} ${DIST} ${TEST} ${OBJECTS} ${DEPENDS}

run: ${EXEC} ${TEST}
	./${EXEC} ${TEST}

${EXEC}: ${OBJECTS}
	${CXX} ${CXXFLAGS} ${OBJECTS} -o $@ ${LDFLAGS}

${OBJDIR}/%.o: ${SRCDIR}/%.cc | ${OBJDIR}
	${CXX} ${CXXFLAGS} -c $< -o $@

${OBJDIR}:
	mkdir $@

%.fin: %.asm tools/asm.py tools/instr.py
	tools/asm.py < $< > $@

${SRCDIR}/opcode.h: tools/instrs tools/generateOpcodes.py tools/instr.py
	tools/generateOpcodes.py > $@

-include ${DEPENDS}
