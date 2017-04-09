#ifndef __STACK_H__
#define __STACK_H__

#include <cstdint>

namespace Fin
{
    class Stack
    {
        char *content;
        int capacity;
        int size;
    public:
        Stack(std::size_t size = 256);
        Stack(const Stack &other) = delete;
        ~Stack();

        template<typename T> void pop(T &val)
        {
            size -= sizeof(T) / sizeof(char);
            val = *reinterpret_cast<T*>(content + size);
        }

        template<typename T> void push(T val)
        {
            *reinterpret_cast<T*>(content + size) = val;
            size += sizeof(T) / sizeof(char);
        }
    };
}

#endif
