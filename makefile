CXX := g++
CXXFLAGS := -std=c++14 -Wall -Wextra -Wno-unused-parameter -MMD -DDEBUG -g
LDFLAGS :=

EXEC := fin
DIST := ${EXEC}.zip

OBJDIR := obj
SRCDIR := src

SOURCES := $(wildcard ${SRCDIR}/*.cc)
OBJECTS := $(patsubst ${SRCDIR}/%.cc,${OBJDIR}/%.o,${SOURCES})
DEPENDS := $(patsubst ${SRCDIR}/%.cc,${OBJDIR}/%.d,${SOURCES})

.PHONY: all dist clean

all: ${EXEC}

dist:
	${RM} ${DIST}
	zip -r ${DIST} Makefile ${SRCDIR}

clean:
	${RM} ${EXEC} ${OBJECTS} ${DEPENDS}

${EXEC}: ${OBJECTS}
	${CXX} ${CXXFLAGS} ${OBJECTS} -o $@ ${LDFLAGS}

${OBJDIR}/%.o: ${SRCDIR}/%.cc | ${OBJDIR}
	${CXX} ${CXXFLAGS} -c $< -o $@

${OBJDIR}:
	mkdir $@

${SRCDIR}/opcode.h: tools/instrs
	tools/generateOpcodes.py > $@

-include ${DEPENDS}
