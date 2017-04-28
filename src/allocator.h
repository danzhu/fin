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
        enum class State
        {
            Stack,
            Allocated,
            Freed,
            Native,
        };

        struct Block
        {
            State state;
            char *value;
            uint32_t size;
        };

        std::vector<Block> heap;
    public:
        Allocator();
        ~Allocator();
        Ptr alloc(uint32_t size);
        void dealloc(Ptr ptr);
        void remove(Ptr ptr);

        template<typename T> Ptr add(T &addr)
        {
            Ptr ptr = heap.size();
            heap.emplace_back(Block{State::Stack,
                    reinterpret_cast<char *>(&addr),
                    sizeof(T)});
            return ptr;
        }

        template<typename T> T &deref(Ptr ptr, uint16_t offset = 0)
        {
            auto block = heap.at(ptr);
            if (block.state == State::Freed || offset + sizeof(T) > block.size)
                throw std::runtime_error{"invalid memory access"};
            return *reinterpret_cast<T *>(block.value + offset);
        }
    };
}

#endif
