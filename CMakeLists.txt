cmake_minimum_required(VERSION 3.1)

project(fin CXX)

# c++ standard
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# build config
set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# warnings
if("${CMAKE_CXX_COMPILER_ID}" STREQUAL "Clang")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} \
    -Weverything \
    -Wno-c++98-compat \
    -Wno-c++98-compat-pedantic \
    -Wno-missing-prototypes \
    -Wno-padded \
    -Wno-sign-conversion \
    -Wno-unused-parameter \
    -Wno-unused-exception-parameter \
    -pedantic")
elseif("${CMAKE_CXX_COMPILER_ID}" STREQUAL "GNU")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} \
    -Wall \
    -Wextra \
    -Wno-unused-parameter \
    -pedantic")
elseif("${CMAKE_CXX_COMPILER_ID}" STREQUAL "MSVC")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} \
    /W4 \
    /wd4100")
else()
    message(WARNING "Compiler not recognized")
endif()

# output paths
SET(EXECUTABLE_OUTPUT_PATH ${PROJECT_BINARY_DIR}/bin)
SET(LIBRARY_OUTPUT_PATH ${PROJECT_BINARY_DIR}/lib)

# files
file(GLOB SOURCES "src/*.cc")
file(GLOB HEADERS "src/*.h")
file(GLOB TOOLS "tools/*.py")

# custom commands
include_directories(${CMAKE_CURRENT_BINARY_DIR})

add_custom_command(
    OUTPUT opcode.h
    DEPENDS meta/instructions tools/opcode.py
    COMMAND tools/opcode.py > "${CMAKE_CURRENT_BINARY_DIR}/opcode.h"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    )

add_custom_command(
    OUTPUT opcode.cc
    DEPENDS meta/instructions tools/opcode.py tools/opname.py
    COMMAND tools/opname.py > "${CMAKE_CURRENT_BINARY_DIR}/opcode.cc"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    )

add_custom_command(
    OUTPUT instructions.md
    DEPENDS meta/instructions tools/instr.py
    COMMAND tools/instr.py > "${CMAKE_CURRENT_BINARY_DIR}/instructions.md"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    )

add_custom_command(
    OUTPUT test.fm
    DEPENDS test.fin ${TOOLS}
    COMMAND tools/compiler.py test.fin -o "${CMAKE_CURRENT_BINARY_DIR}/test.fm"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    )

# targets
add_executable(fin ${SOURCES} ${HEADERS} opcode.h opcode.cc)

add_custom_target(doc DEPENDS instructions.md)

add_custom_target(run
    COMMAND fin ${CMAKE_CURRENT_BINARY_DIR}/test.fm
    DEPENDS test.fm)

# options
option(DEBUG "Enable debug messages" OFF)

if(DEBUG)
    target_compile_definitions(fin PRIVATE DEBUG=${DEBUG})
endif()
