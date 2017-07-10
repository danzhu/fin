#ifndef FIN_ALLOCATOR_H
#define FIN_ALLOCATOR_H

#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include "log.h"
#include "typedefs.h"

namespace Fin
{
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

        char *deref(uint32_t blk, uint32_t offset, uint32_t size) const
        {
            auto block = heap.at(blk);
            if (block.state == State::Freed || offset + size > block.size)
                throw std::runtime_error{"invalid memory access at "
                    + std::to_string(offset + size) + " out of "
                    + std::to_string(block.size)};
            return block.value + offset;
        }

    public:
        Allocator() {}

        ~Allocator()
        {
            // cleanup any blocks still in-use
            for (auto val : heap)
            {
                if (val.state == State::Allocated)
                    std::free(val.value);
            }
        }

        Ptr alloc(uint32_t size)
        {
            // TODO: reuse deallocated ptrs
            auto ptr = static_cast<Ptr>(heap.size()) << 32;
            auto mem = static_cast<char *>(std::malloc(size));

            if (!mem)
                throw std::runtime_error{"failed to allocate"};

            heap.emplace_back(Block{State::Allocated, mem, size});
            return ptr;
        }

        Ptr add(char *addr, uint32_t size)
        {
            auto ptr = static_cast<Ptr>(heap.size()) << 32;
            heap.emplace_back(Block{State::Native, addr, size});
            return ptr;
        }

        void dealloc(Ptr ptr)
        {
            uint32_t blk = ptr >> 32;
            auto &val = heap.at(blk);

            if (val.state != State::Allocated)
                throw std::runtime_error{"invalid deallocation"};

            std::free(val.value);
            val.state = State::Freed;
        }

        Ptr realloc(Ptr ptr, uint32_t size)
        {
            uint32_t blk = ptr >> 32;
            auto &val = heap.at(blk);

            if (val.state != State::Allocated)
                throw std::runtime_error{"invalid reallocation"};

            val.value = static_cast<char *>(std::realloc(val.value, size));

            if (!val.value)
                throw std::runtime_error{"failed to reallocate"};

            val.size = size;

            return ptr;
        }

        void remove(Ptr ptr)
        {
            uint32_t blk = ptr >> 32;
            auto &val = heap.at(blk);

            val.state = State::Freed;
        }

        char *read(Ptr ptr, uint32_t size) const
        {
            uint32_t blk = ptr >> 32;
            uint32_t offset = ptr & 0xFFFFFFFF;

            LOG(2) << std::endl << "  & " << blk << ':' << offset;

            return deref(blk, offset, size);
        }

        char *write(Ptr ptr, uint32_t size) const
        {
            uint32_t blk = ptr >> 32;
            uint32_t offset = ptr & 0xFFFFFFFF;

            LOG(2) << std::endl << "  * " << blk << ':' << offset;

            return deref(blk, offset, size);
        }

        template<typename T> Ptr add(T &addr)
        {
            Ptr ptr = heap.size();
            heap.emplace_back(Block{State::Stack,
                    reinterpret_cast<char *>(&addr),
                    sizeof(T)});
            return ptr;
        }
    };
}

#endif
