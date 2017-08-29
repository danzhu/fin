cmake_minimum_required(VERSION 3.5)

project(fin CXX)

# options
option(DEBUG "Enable debug messages logging" 0)
option(PEDANTIC "Disable auto-handling of execution errors" OFF)

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
    -Wno-covered-switch-default \
    -Wno-missing-prototypes \
    -Wno-padded \
    -Wno-sign-conversion \
    -Wno-unused-exception-parameter \
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
    message(WARNING "Compiler not recognized, no warning flags set")
endif()

# files
set(PY "${PROJECT_SOURCE_DIR}/py")
set(GEN "${CMAKE_CURRENT_BINARY_DIR}/gen")

file(GLOB SOURCES "src/*.cc")
file(GLOB_RECURSE HEADERS "include/*.h")
file(GLOB MAIN "main/*.cc")
file(GLOB FINC "${PY}/finc/*.py")

file(MAKE_DIRECTORY "${GEN}")

# custom commands
add_custom_command(
    OUTPUT "${GEN}/opcode.h"
    DEPENDS "${PY}/instructions" "${PY}/instr.py" "${PY}/opcode.py"
    COMMAND "${PY}/opcode.py" > "${GEN}/opcode.h")

add_custom_command(
    OUTPUT "${GEN}/opcode.cc"
    DEPENDS "${PY}/instructions" "${PY}/instr.py" "${PY}/opname.py"
    COMMAND "${PY}/opname.py" > "${GEN}/opcode.cc")

add_custom_command(
    OUTPUT instructions.md
    DEPENDS "${PY}/instructions" "${PY}/instr.py"
    COMMAND "${PY}/instr.py" > instructions.md)

add_custom_command(
    OUTPUT test.fm
    DEPENDS "${PROJECT_SOURCE_DIR}/test.fin" "${PY}/compiler.py" "${PY}/asm.py"
        ${FINC}
    COMMAND "${PY}/compiler.py" "${PROJECT_SOURCE_DIR}/test.fin" -o test.fm)

# targets
add_library(fin
    ${SOURCES} ${HEADERS}
    "${GEN}/opcode.cc" "${GEN}/opcode.h" "${PY}/instructions")
target_include_directories(fin PRIVATE "${GEN}")
target_include_directories(fin PUBLIC "${PROJECT_SOURCE_DIR}/include")

add_executable(fin-bin ${MAIN})
set_target_properties(fin-bin PROPERTIES OUTPUT_NAME fin)
target_link_libraries(fin-bin fin)

add_custom_target(doc DEPENDS instructions.md)

add_custom_target(run
    COMMAND fin-bin test.fm
    DEPENDS test.fm)

# preprocessor definitions
if(DEBUG)
    target_compile_definitions(fin PUBLIC FIN_DEBUG=${DEBUG})
endif()

if(PEDANTIC)
    target_compile_definitions(fin PRIVATE FIN_PEDANTIC=1)
endif()

# tests
enable_testing()

# macro for testing compilation process
macro(test_compile name)
    add_test(NAME ${name}
        COMMAND "${PY}/compiler.py" "${PROJECT_SOURCE_DIR}/test/${name}.fin")

    if(${ARGC} GREATER 1)
        set_tests_properties(${name} PROPERTIES
            PASS_REGULAR_EXPRESSION ${ARGV1})
    endif()
endmacro()

test_compile("overload")

test_compile("no_implicit_cast" "Float cannot be converted to Int")
test_compile("generic_generic" "generic type cannot have generic arguments")
test_compile("no_overload" "no viable function overload")
test_compile("infer_failed" "unable to infer type")
test_compile("resolve_failed" "cannot resolve function overload")
test_compile("diverge_var" "cannot create variable of type Diverge")
test_compile("init_mismatch" "initialization level mismatch")
test_compile("no_type" "type is required when not assigning a value")
test_compile("generic_unmatched" "unmatched generic arguments")
test_compile("member_nonstruct" "member access requires struct type")
test_compile("void_var" "cannot create variable of type Void")
test_compile("args_unmatched" "no viable function overload")
test_compile("no_symbol" "cannot find symbol 'i'")
test_compile("unsized_array" "cannot create variable of unsized array type")
