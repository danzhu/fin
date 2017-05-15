function :inc(Int)Int end_inc
load_arg -4 4
const_i 1
return_val 4
end_inc:

const_i 123
call :inc(Int)Int 4
call fin:print(Int) 4
