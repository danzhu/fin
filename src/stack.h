#ifndef FIN_STACK_H
#define FIN_STACK_H

#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include "log.h"
#include "type.h"
#include "typedefs.h"
#include "util.h"

namespace Fin
{
    class Stack
    {
        char *_content = nullptr;
        std::uint32_t _cap;
        std::uint32_t _size = 0;
    public:
        explicit Stack(Size cap):
            _content{new char[cap]}, _cap{cap} {}

        Stack(const Stack &other) = delete;
        Stack(Stack &&other) = delete;

        ~Stack()
        {
            delete[] _content;
        }

        Stack &operator=(const Stack &other) = delete;
        Stack &operator=(Stack &&other) = delete;

        std::uint32_t size() const noexcept { return _size; }
        void resize(std::uint32_t size) noexcept { _size = size; }

        char *content() const noexcept { return _content; }
        std::uint32_t capacity() const noexcept { return _cap; }

        char *at(Offset idx, Size size)
        {
            if (idx + size > _size)
                throw std::out_of_range{"invalid stack access at "
                    + std::to_string(idx) + ", size " + std::to_string(size)};

            return _content + idx;
        }

        char *pushSize(Size size)
        {
            if (_size > _cap - size)
                throw std::overflow_error{"stack overflow"};

            auto val = &_content[_size];

            LOG(2) << std::endl << "  < [" << _size << ", " << size << "]";

            _size += size;
            return val;
        }

        char *popSize(Size size)
        {
            if (_size < size)
                throw std::overflow_error{"negative stack size"};

            LOG(2) << std::endl << "  > [" << _size << ", " << size << "]";

            _size -= size;
            return &_content[_size];
        }

        char *topSize(Size size)
        {
            if (_size < size)
                throw std::overflow_error{"accessing at negative index"};

            LOG(2) << std::endl << "  ^ [" << _size << ", " << size << "]";

            return &_content[_size - size];
        }

        template<typename T> T &at(Offset idx)
        {
            constexpr auto size = alignTo(sizeof(T), MAX_ALIGN);

            return *reinterpret_cast<T*>(at(idx, size));
        }

        template<typename T> void push(T val)
        {
            constexpr auto size = alignTo(sizeof(T), MAX_ALIGN);

            if (_size > _cap - size)
                throw std::overflow_error{"stack overflow"};

            LOG(2) << std::endl << "  < " << val;
            LOG(2) << " [" << _size << ", " << size << "]";

            auto addr = _size;
            _size += size;
            at<T>(addr) = val;
        }

        template<typename T> void pop(T &val)
        {
            constexpr auto size = alignTo(sizeof(T), MAX_ALIGN);

            if (_size < size)
                throw std::overflow_error{"negative stack size"};

            val = at<T>(_size - size);

            LOG(2) << std::endl << "  > " << val;
            LOG(2) << " [" << _size << ", " << size << "]";

            _size -= size;
        }

        template<typename T> T pop()
        {
            T val;
            pop(val);
            return val;
        }

        template<typename T> T &top()
        {
            constexpr auto size = alignTo(sizeof(T), MAX_ALIGN);

            if (_size < size)
                throw std::runtime_error{"accessing at negative index"};

            auto &val = at<T>(_size - size);

            LOG(2) << std::endl << "  ^ " << val;
            LOG(2) << " [" << _size << ", " << size << "]";

            return val;
        }
    };
}

#endif
