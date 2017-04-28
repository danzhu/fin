#ifndef __ALLOCATOR_H__
#define __ALLOCATOR_H__

#include <cstdint>
#include <stdexcept>
#include <vector>

namespace Fin
{
    typedef uint64_t Ptr;

    class Allocator
    {
        const int OFFSET_WIDTH = 32;

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
        Ptr add(char *addr, uint32_t size);
        void dealloc(Ptr ptr);
        void remove(Ptr ptr);

        char *deref(Ptr ptr, uint32_t size) const
        {
            auto block = heap.at(ptr >> OFFSET_WIDTH);
            auto offset = ptr & ((1l << OFFSET_WIDTH) - 1);
            if (block.state == State::Freed || offset + size > block.size)
                throw std::runtime_error{"invalid memory access at "
                    + std::to_string(offset + size) + " out of "
                    + std::to_string(block.size)};
            return block.value + offset;
        }

        template<typename T> Ptr add(T &addr)
        {
            Ptr ptr = heap.size();
            heap.emplace_back(Block{State::Stack,
                    reinterpret_cast<char *>(&addr),
                    sizeof(T)});
            return ptr;
        }

        template<typename T> T &deref(Ptr ptr) const
        {
            return *reinterpret_cast<T *>(deref(ptr, sizeof(T)));
        }
    };
}

#endif
