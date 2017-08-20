#ifndef FIN_STACK_H
#define FIN_STACK_H

#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include "allocator.h"
#include "log.h"
#include "type.h"
#include "typedefs.h"
#include "typeinfo.h"
#include "util.h"

namespace Fin
{
    class Stack
    {
        public:
            Stack(Allocator &alloc, Offset cap = Offset{4096}):
                _alloc{alloc}
            {
                _ptr = alloc.alloc(cap,
                        Allocator::Access::Read |
                        Allocator::Access::Write);

                _data = alloc.get(_ptr);
                _capacity = cap;
            }

            Ptr ptr() const noexcept { return _ptr; }

            Offset size() const noexcept { return _size; }

            void resize(Offset size) noexcept
            {
                _size = size;
                _alloc.setSize(_ptr, size);
            }

            Memory at(Offset off, TypeInfo type)
            {
                if (off + type.maxAlignedSize() > _size)
                    throw std::out_of_range{"invalid stack access"};

                return Memory{_data + off};
            }

            Memory pushSize(TypeInfo type)
            {
                if (_size + type.maxAlignedSize() > _capacity)
                    throw std::overflow_error{"stack overflow"};

                LOG(2) << std::endl << "  < [" << _size << ", "
                    << type.maxAlignedSize() << "]";

                Memory mem{_data + _size};
                resize(_size + type.maxAlignedSize());
                return mem;
            }

            Memory popSize(TypeInfo type)
            {
                if (_size < type.maxAlignedSize())
                    throw std::overflow_error{"negative stack size"};

                LOG(2) << std::endl << "  > [" << _size << ", "
                    << type.maxAlignedSize() << "]";

                resize(_size - type.maxAlignedSize());
                return Memory{_data + _size};
            }

            Memory topSize(TypeInfo type)
            {
                if (_size < type.maxAlignedSize())
                    throw std::overflow_error{"accessing at negative index"};

                LOG(2) << std::endl << "  ^ [" << _size << ", "
                    << type.maxAlignedSize() << "]";

                return Memory{_data + _size - type.maxAlignedSize()};
            }

            template<typename T>
            void push(T val)
            {
                constexpr auto size = TypeInfo::maxAlignedSize<T>();

                LOG(2) << std::endl << "  < " << val;
                LOG(2) << " [" << _size << ", " << size << "]";

                Memory{_data + _size}.as<T>() = val;
                resize(_size + size);
            }

            template<typename T>
            T pop()
            {
                constexpr auto size = TypeInfo::maxAlignedSize<T>();

                if (_size < size)
                    throw std::overflow_error{"negative stack size"};

                auto val = Memory{_data + _size - size}.as<T>();

                LOG(2) << std::endl << "  > " << val;
                LOG(2) << " [" << _size << ", " << size << "]";

                resize(_size - size);
                return val;
            }

            template<typename T>
            void pop(T &val)
            {
                val = pop<T>();
            }

            template<typename T>
            T &top()
            {
                constexpr auto size = TypeInfo::maxAlignedSize<T>();

                if (_size < size)
                    throw std::runtime_error{"accessing at negative index"};

                auto &val = Memory{_data + _size - size}.as<T>();

                LOG(2) << std::endl << "  ^ " << val;
                LOG(2) << " [" << _size << ", " << size << "]";

                return val;
            }

        private:
            Allocator &_alloc;
            Memory _data;
            Ptr _ptr;
            Offset _size;
            Offset _capacity;
    };
}

#endif
