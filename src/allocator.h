#ifndef __ALLOCATOR_H__
#define __ALLOCATOR_H__

#include <cstdint>
#include <stdexcept>
#include <vector>

namespace Fin
{
    typedef uint32_t Ptr;

    class Allocator
    {
        struct Block
        {
            char *value;
            uint32_t size;
        };

        std::vector<Block> heap;
    public:
        Allocator();
        ~Allocator();
        Ptr alloc(uint32_t size);
        void dealloc(Ptr ptr);

        template<typename T> T &deref(Ptr ptr, uint16_t offset = 0)
        {
            auto block = heap.at(ptr);
            if (offset + sizeof(T) > block.size)
                throw std::runtime_error{"invalid memory access"};
            return *reinterpret_cast<T *>(block.value + offset);
        }
    };
}

#endif
