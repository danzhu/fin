#include "fin/stack.h"

#include "fin/allocator.h"
#include "fin/util.h"

Fin::Stack::Stack(Allocator &alloc, Offset cap) : _alloc{alloc}
{
    _ptr = alloc.alloc(cap, Allocator::Access::Read | Allocator::Access::Write);

    _data = alloc.get(_ptr);
    _capacity = cap;
}

void Fin::Stack::resize(Offset size) noexcept
{
    _size = size;
    _alloc.setSize(_ptr, size);
}

Fin::Memory Fin::Stack::at(Offset off, TypeInfo type)
{
    if (off + type.maxAlignedSize() > _size)
        throw RuntimeError{"invalid stack access"};

    return Memory{_data + off};
}

Fin::Memory Fin::Stack::pushSize(TypeInfo type)
{
    if (_size + type.maxAlignedSize() > _capacity)
        throw RuntimeError{"stack overflow"};

    LOG(2) << "\n  < [" << _size << ", " << type.maxAlignedSize() << "]";

    Memory mem{_data + _size};
    resize(_size + type.maxAlignedSize());
    return mem;
}

Fin::Memory Fin::Stack::popSize(TypeInfo type)
{
    if (_size < type.maxAlignedSize())
        throw RuntimeError{"negative stack size"};

    LOG(2) << "\n  > [" << _size << ", " << type.maxAlignedSize() << "]";

    resize(_size - type.maxAlignedSize());
    return Memory{_data + _size};
}

Fin::Memory Fin::Stack::topSize(TypeInfo type)
{
    if (_size < type.maxAlignedSize())
        throw RuntimeError{"accessing at negative index"};

    LOG(2) << "\n  ^ [" << _size << ", " << type.maxAlignedSize() << "]";

    return Memory{_data + _size - type.maxAlignedSize()};
}
