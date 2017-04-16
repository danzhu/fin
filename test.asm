module test 1

method_ref 0
module_ref io
method_ref 0
method_ref 1

# ------ method 0 ------
method 0 4 method_0
load_i -4
call 1
ret
method_0:

# ------ main ------
push 8

# max = read()
call 2
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
