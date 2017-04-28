module 'test'

# ------ method 0 ------
method 'print' 4 method_0
load_arg_4 -4
call 2
return
method_0:

# ------ method 1 ------
method 'input' 0 method_1
call 3
return_4
method_1:

# ------ references ------

ref_module 'io'
ref_method 'print'
ref_method 'input'
ref_method 'write'
ref_method 'read'

# ------ main ------
push 16

# max = read()
call 1
store_arg_4 0

# i = 0
const_i 0
store_arg_4 4

# while
br cond_while

begin_while:
# write(i)
load_arg_4 4
call 0

# i = i + 1
load_arg_4 4
const_i 1
add_i
store_arg_4 4

cond_while:
# i < max
load_arg_4 4
load_arg_4 0
lt_i

# loop
br_true begin_while

# ptr = alloc(4)
const_i 4
alloc
store_arg_4 8

# *ptr = i
load_arg_4 8
load_arg_4 4
store_ptr_4 0

# write(*ptr)
load_arg_4 8
load_ptr_4 0
call 0
