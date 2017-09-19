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

# compiler flags
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

    if(CMAKE_GENERATOR STREQUAL "Ninja")
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fcolor-diagnostics")
    endif()
elseif("${CMAKE_CXX_COMPILER_ID}" STREQUAL "GNU")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} \
        -Wall \
        -Wextra \
        -Wno-unused-parameter \
        -pedantic")

    if(CMAKE_GENERATOR STREQUAL "Ninja")
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fdiagnostics-color=always")
    endif()
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

file(GLOB_RECURSE SOURCES "${PROJECT_SOURCE_DIR}/src/*.cc")
file(GLOB_RECURSE HEADERS "${PROJECT_SOURCE_DIR}/include/*.h")
file(GLOB_RECURSE MAIN "${PROJECT_SOURCE_DIR}/main/*.cc")
file(GLOB_RECURSE FINC "${PY}/finc/*.py")

file(MAKE_DIRECTORY "${GEN}")

# custom commands
add_custom_command(
    OUTPUT "${GEN}/opcode.h"
    DEPENDS "${PY}/instructions" "${PY}/instrs.py" "${PY}/opcode.py"
    COMMAND "${PY}/opcode.py" > "${GEN}/opcode.h")

add_custom_command(
    OUTPUT "${GEN}/opcode.cc"
    DEPENDS "${PY}/instructions" "${PY}/instrs.py" "${PY}/opname.py"
    COMMAND "${PY}/opname.py" > "${GEN}/opcode.cc")

add_custom_command(
    OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/instructions.md"
    DEPENDS "${PY}/instructions" "${PY}/instrs.py"
    COMMAND "${PY}/instrs.py" > "${CMAKE_CURRENT_BINARY_DIR}/instructions.md")

add_custom_command(
    OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/test.fm"
    DEPENDS "${PROJECT_SOURCE_DIR}/test.fin" "${PY}/compiler.py" "${PY}/asm.py"
        ${FINC}
    COMMAND "${PY}/compiler.py" "${PROJECT_SOURCE_DIR}/test.fin"
        -o "${CMAKE_CURRENT_BINARY_DIR}/test.fm")

set_source_files_properties("${GEN}/opcode.h" "${GEN}/opcode.cc"
    PROPERTIES GENERATED TRUE)

# targets
add_library(fin ${SOURCES} "${GEN}/opcode.cc" ${HEADERS} "${GEN}/opcode.h")
target_include_directories(fin PRIVATE "${GEN}")
target_include_directories(fin PUBLIC "${PROJECT_SOURCE_DIR}/include")

add_executable(fin-bin ${MAIN})
set_target_properties(fin-bin PROPERTIES OUTPUT_NAME fin)
target_link_libraries(fin-bin fin)

add_custom_target(doc DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/instructions.md")

add_custom_target(run
    COMMAND fin-bin "${CMAKE_CURRENT_BINARY_DIR}/test.fm"
    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/test.fm")

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
macro(test_compile name regex)
    add_test(NAME ${name} COMMAND
        "${PY}/compiler.py" "${PROJECT_SOURCE_DIR}/test/${name}.fin")

    set_tests_properties(${name} PROPERTIES
        PASS_REGULAR_EXPRESSION ${regex})
endmacro()

macro(test_exec name)
    add_test(NAME ${name} COMMAND
        ${CMAKE_COMMAND}
        -DCOMPILER=${PY}/compiler.py
        -DFIN=$<TARGET_FILE:fin-bin>
        -DINPUT=${PROJECT_SOURCE_DIR}/test/${name}.fin
        -P ${PROJECT_SOURCE_DIR}/TestExec.cmake)
endmacro()

test_compile("args_unmatched" "no viable function overload")
test_compile("diverge_var" "cannot create variable of type Diverge")
test_compile("generic_generic" "generic type cannot have generic arguments")
test_compile("generic_unmatched" "unmatched generic arguments")
test_compile("infer_failed" "unable to infer type")
test_compile("jump_in_condition" "jump not in a while loop")
test_compile("member_missing" "cannot find member 'missing'")
test_compile("member_nonstruct" "member access requires struct type")
test_compile("no_implicit_cast" "Float cannot be converted to Int")
test_compile("no_overload" "no viable function overload")
test_compile("no_type" "type is required when not assigning a value")
test_compile("redefine_as_function" "redefining 'Fn' as function")
test_compile("ref_in_scope" "reference 'rt' already in scope")
test_compile("resolve_failed" "cannot resolve function overload")
test_compile("symbol_exists" "symbol 'Test' already exists")
test_compile("symbol_missing" "cannot find symbol 'i'")
test_compile("unsized_array" "cannot create variable of unsized array type")
test_compile("void_var" "cannot create variable of type Void")

test_exec("generic_struct")
test_exec("pattern_enum")
test_exec("pattern_int")
test_exec("pattern_struct")

# TODO
# test_compile("recursive_struct" "recursive type definition")
