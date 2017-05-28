#ifndef FIN_STACK_H
#define FIN_STACK_H

#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include "log.h"

namespace Fin
{
    class Stack
    {
        char *_content = nullptr;
        uint32_t _cap;
        uint32_t _size = 0;
    public:
        explicit Stack(uint32_t cap = 256): _content{new char[cap]}, _cap{cap}
        {}
        Stack(const Stack &other) = delete;
        ~Stack()
        {
            delete[] _content;
        }

        Stack &operator=(const Stack &other) = delete;

        uint32_t size() const noexcept { return _size; }
        void resize(uint32_t size) noexcept { _size = size; }

        char *content() const noexcept { return _content; }
        uint32_t capacity() const noexcept { return _cap; }

        char *at(uint32_t idx, uint32_t size)
        {
            if (idx + size > _size)
                throw std::out_of_range{"invalid stack access at "
                    + std::to_string(idx) + ", size " + std::to_string(size)};

            return _content + idx;
        }

        char *push(uint16_t size)
        {
            if (_size + size > _cap)
                throw std::overflow_error{"stack overflow"};

            auto val = &_content[_size];
            _size += size;

            LOG(2) << std::endl << "  < [" << _size << ", " << size << "]";

            return val;
        }

        char *pop(uint16_t size)
        {
            if (_size < size)
                throw std::overflow_error{"negative stack size"};

            _size -= size;

            LOG(2) << std::endl << "  > [" << _size << ", " << size << "]";

            return &_content[_size];
        }

        template<typename T> T &at(uint32_t idx)
        {
            return *reinterpret_cast<T*>(at(idx, sizeof(T)));
        }

        template<typename T> void pop(T &val)
        {
            if (_size < sizeof(T))
                throw std::overflow_error{"negative stack size"};

            val = at<T>(_size - sizeof(T));
            _size -= sizeof(T);

            LOG(2) << std::endl << "  > " << val;
            LOG(2) << " [" << _size << ", " << sizeof(T) << "]";
        }

        template<typename T> T pop()
        {
            T val;
            pop(val);
            return val;
        }

        template<typename T> void push(T val)
        {
            if (_size + sizeof(T) > _cap)
                throw std::overflow_error{"stack overflow"};

            LOG(2) << std::endl << "  < " << val;
            LOG(2) << " [" << _size << ", " << sizeof(T) << "]";

            auto addr = _size;
            _size += sizeof(T);
            at<T>(addr) = val;
        }
    };
}

#endif
