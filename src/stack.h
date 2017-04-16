#ifndef __STACK_H__
#define __STACK_H__

#include <cstdint>
#include <stdexcept>

namespace Fin
{
    class Stack
    {
        char *_content = nullptr;
        uint32_t _cap;
        uint32_t _size = 0;
    public:
        Stack(uint32_t cap = 256);
        Stack(const Stack &other) = delete;
        ~Stack();

        Stack &operator=(const Stack &other) = delete;

        uint32_t size() const noexcept { return _size; }
        void resize(uint32_t size) noexcept { _size = size; }

        template<typename T> T &at(uint32_t idx)
        {
            // note that we allow access to exactly _size
            // so that things can be pushed
            if (idx > _size)
                throw std::length_error{"invalid stack access"};

            return *reinterpret_cast<T*>(_content + idx);
        }

        template<typename T> T pop()
        {
            if (_size < sizeof(T))
                throw std::overflow_error{"negative stack size"};

            _size -= sizeof(T);
            return at<T>(_size);
        }

        template<typename T> void pop(T &val)
        {
            val = pop<T>();
        }

        template<typename T> void push(T val)
        {
            at<T>(_size) = val;
            _size += sizeof(T);

            if (_size > _cap)
                throw std::overflow_error{"stack overflow"};
        }
    };
}

#endif
