#ifndef FIN_STACK_H
#define FIN_STACK_H

#include "exception.h"
#include "log.h"
#include "memory.h"
#include "typedefs.h"
#include "typeinfo.h"
#include <iostream>
#include <string>

namespace Fin
{
class Allocator;

class Stack
{
public:
    explicit Stack(Allocator &alloc, Offset cap = Offset{4096});

    void resize(Offset size) noexcept;
    Memory at(Offset off, TypeInfo type);
    Memory pushSize(TypeInfo type);
    Memory popSize(TypeInfo type);
    Memory topSize(TypeInfo type);

    Ptr ptr() const noexcept { return _ptr; }
    Offset size() const noexcept { return _size; }

    template <typename T>
    void push(T val)
    {
        constexpr auto size = TypeInfo::maxAlignedSize<T>();

        if (_size + size > _capacity)
            throw RuntimeError{"stack overflow"};

        LOG(2) << "\n  < " << val << " [" << _size << ", " << size << "]";

        Memory{_data + _size}.as<T>() = val;
        resize(_size + size);
    }

    template <typename T>
    T pop()
    {
        constexpr auto size = TypeInfo::maxAlignedSize<T>();

        if (_size < size)
            throw RuntimeError{"negative stack size"};

        auto val = Memory{_data + _size - size}.as<T>();

        LOG(2) << "\n  > " << val << " [" << _size << ", " << size << "]";

        resize(_size - size);
        return val;
    }

    template <typename T>
    void pop(T &val)
    {
        val = pop<T>();
    }

    template <typename T>
    T &top()
    {
        constexpr auto size = TypeInfo::maxAlignedSize<T>();

        if (_size < size)
            throw RuntimeError{"accessing at negative index"};

        auto &val = Memory{_data + _size - size}.as<T>();

        LOG(2) << "\n  ^ " << val << " [" << _size << ", " << size << "]";

        return val;
    }

private:
    Allocator &_alloc;
    Memory _data;
    Ptr _ptr;
    Offset _size;
    Offset _capacity;
};
} // namespace Fin

#endif
