#ifndef FIN_ALLOCATOR_H
#define FIN_ALLOCATOR_H

#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include "log.h"

namespace Fin
{
    typedef uint64_t Ptr;

    class Allocator
    {
        const uint32_t OFFSET_WIDTH = 32;

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
            auto id = static_cast<uint32_t>(ptr >> OFFSET_WIDTH);
            auto offset = ptr & ((UINT64_C(1) << OFFSET_WIDTH) - 1);

            LOG(2) << std::endl << "  * " << id << ':' << offset;

            auto block = heap.at(id);
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
