lib 'main'

ref_lib 'rt'
ref_fn 'print(Int)'
ref_fn 'alloc(Int)&[0]'

type 'Vec' 1 END_Vec
    !sz T
    !sz Ptr
    size_p
    !sz Int
    size_i

    !off content
    local Ptr
    !off size
    local Int
    !off capacity
    local Int

    type_ret
END_Vec:
    member 'content'
    member 'size'
    member 'capacity'

fn 'new(Int)main:Vec{0}' 1 0 BEGIN_new END_new
    !sz T
    !sz Int
    size_i
    !sz Vec{T}
    size_dup T
    type_call main:Vec

    !off Vec{T}:content
    type_mem main:Vec:content
    !off Vec{T}:size
    type_mem main:Vec:size
    !off Vec{T}:capacity
    type_mem main:Vec:capacity
    !sz Ptr
    size_p

    !ctr rt:alloc(Int)&[0]
    size_dup T
    contract rt:alloc(Int)&[0]

    !off cap
    param Int
    !off v
    local Vec{T}

    sign
BEGIN_new:
    # Vec(rt:alloc(cap), 0, cap)
    # content = rt:alloc(cap)
    addr_var v
    addr_mem Vec{T}:content
    addr_arg cap
    load Int
    call rt:alloc(Int)&[0]
    store Ptr

    # size = 0
    addr_var v
    addr_mem Vec{T}:size
    const_i 0
    store Int

    # capacity = cap
    addr_var v
    addr_mem Vec{T}:capacity
    addr_arg cap
    load Int
    store Int

    addr_var v
    load Vec{T}

    ret Vec{T}
END_new:

fn 'main()' 0 0 BEGIN_test END_test
    !sz Vec{Int}
    size_i
    type_call main:Vec

    !off Vec{Int}:size
    type_mem main:Vec:size

    !sz Int
    size_i

    !ctr main:new(Int)main:Vec{Int}
    size_i
    contract main:new(Int)main:Vec{0}
    !ctr rt:print(Int)
    contract rt:print(Int)

    !off v
    local Vec{Int}

    sign
BEGIN_test:
    # v = new(2)
    addr_var v
    const_i 2
    call main:new(Int)main:Vec{Int}
    store Vec{Int}

    # v.size.rt:print()
    addr_var v
    addr_mem Vec{Int}:size
    load Int
    call rt:print(Int)

    end
END_test:
