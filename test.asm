module 'test'

# ------ method 0 ------
method 'print' 4 method_0
load_i -4
call 2
return
method_0:

# ------ method 1 ------
method 'input' 0 method_1
call 3
return_i
method_1:

# ------ references ------

ref_module 'io'
ref_method 'print'
ref_method 'input'
ref_method 'write'
ref_method 'read'

# ------ main ------
push 8

# max = read()
call 1
store_i 0

# i = 0
const_i 0
store_i 4

# while
br cond_while

begin_while:
# write(i)
load_i 4
call 0

# i = i + 1
load_i 4
const_i 1
add_i
store_i 4

cond_while:
# i < max
load_i 4
load_i 0
lt_i

# loop
br_true begin_while
