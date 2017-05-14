cmake_minimum_required(VERSION 3.1)

project(fin)

# c++ standard
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# build config
set(CMAKE_BUILD_TYPE Debug)
option(LOG_OPNAME "Log opnames for instructions" OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(LOG_OPNAME)
    add_definitions(-DDEBUG)
endif()

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

# custom commands
include_directories(${CMAKE_CURRENT_BINARY_DIR})

add_custom_command(
    OUTPUT opcode.h
    DEPENDS meta/instructions
    COMMAND tools/opcode.py > "${CMAKE_CURRENT_BINARY_DIR}/opcode.h"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    )

add_custom_command(
    OUTPUT opcode.cc
    DEPENDS meta/instructions
    COMMAND tools/opname.py > "${CMAKE_CURRENT_BINARY_DIR}/opcode.cc"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    )

add_custom_command(
    OUTPUT instructions.md
    DEPENDS meta/instructions
    COMMAND tools/instr.py > "${CMAKE_CURRENT_BINARY_DIR}/instructions.md"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    )

# targets
file(GLOB SOURCES "src/*.cc")
add_executable(${PROJECT_NAME} ${SOURCES} opcode.h opcode.cc)

add_custom_target(doc DEPENDS instructions.md)
