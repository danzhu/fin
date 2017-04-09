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

all: ${EXEC} asm

dist:
	${RM} ${DIST}
	zip -r ${DIST} Makefile ${SRCDIR}

clean:
	${RM} ${EXEC} asm ${OBJECTS} ${DEPENDS}

${EXEC}: ${OBJECTS}
	${CXX} ${CXXFLAGS} ${OBJECTS} -o $@ ${LDFLAGS}

asm: asm.cc
	${CXX} ${CXXFLAGS} asm.cc -o $@

${OBJDIR}/%.o: ${SRCDIR}/%.cc | ${OBJDIR}
	${CXX} ${CXXFLAGS} -c $< -o $@

${OBJDIR}:
	mkdir $@

-include ${DEPENDS}
