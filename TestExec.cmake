execute_process(COMMAND ${COMPILER} ${INPUT} -o test.fm RESULT_VARIABLE res)
if(res)
    message(FATAL_ERROR "Compilation failed")
endif()

execute_process(COMMAND ${FIN} test.fm RESULT_VARIABLE res)
if(res)
    message(FATAL_ERROR "Execution failed")
endif()
