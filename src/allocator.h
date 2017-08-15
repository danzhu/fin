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
        public:
            Allocator();
            ~Allocator() noexcept;

            Ptr alloc(std::uint32_t size);
            Ptr add(char *addr, std::uint32_t size);
            void dealloc(Ptr ptr);
            Ptr realloc(Ptr ptr, uint32_t size);
            void remove(Ptr ptr);
            char *read(Ptr ptr, std::uint32_t size) const;
            char *write(Ptr ptr, std::uint32_t size);
            void summary(std::ostream &out) const noexcept;

        private:
            enum class State
            {
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
                    std::uint32_t size) const;
    };
}

#endif
