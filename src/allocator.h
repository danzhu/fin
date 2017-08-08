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
            std::uint32_t size;
        };

        std::vector<Block> heap;

        char *deref(std::uint32_t blk, std::uint32_t offset,
                std::uint32_t size) const
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

        Ptr alloc(std::uint32_t size)
        {
            // TODO: reuse deallocated ptrs
            Ptr ptr{static_cast<std::uint32_t>(heap.size()), 0};
            auto addr = static_cast<char *>(std::malloc(size));

            if (!addr)
                throw std::runtime_error{"failed to allocate"};

            heap.emplace_back(Block{State::Allocated, addr, size});
            return ptr;
        }

        Ptr add(char *addr, std::uint32_t size)
        {
            Ptr ptr{static_cast<std::uint32_t>(heap.size()), 0};
            heap.emplace_back(Block{State::Native, addr, size});
            return ptr;
        }

        void dealloc(Ptr ptr)
        {
            auto &val = heap.at(ptr.block);

            if (val.state != State::Allocated)
                throw std::runtime_error{"invalid deallocation"};

            std::free(val.value);
            val.state = State::Freed;
        }

        Ptr realloc(Ptr ptr, uint32_t size)
        {
            auto &val = heap.at(ptr.block);

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
            auto &val = heap.at(ptr.block);

            val.state = State::Freed;
        }

        char *read(Ptr ptr, std::uint32_t size) const
        {
            LOG(2) << std::endl << "  & " << ptr;

            return deref(ptr.block, ptr.offset, size);
        }

        char *write(Ptr ptr, std::uint32_t size) const
        {
            LOG(2) << std::endl << "  * " << ptr;

            return deref(ptr.block, ptr.offset, size);
        }
    };
}

#endif
