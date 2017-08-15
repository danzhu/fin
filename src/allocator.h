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
            enum class State
            {
                ReadOnly,
                Native,
                Managed,
                Freed,
            };

            Allocator();
            ~Allocator() noexcept;

            Ptr alloc(std::uint32_t size, State state = State::Managed);
            Ptr add(char *addr, std::uint32_t size,
                    State state = State::Native);
            void remove(Ptr ptr);
            void dealloc(Ptr ptr);
            Ptr realloc(Ptr ptr, std::uint32_t size);
            char *read(Ptr ptr, std::uint32_t size);
            char *write(Ptr ptr, std::uint32_t size);
            void summary(std::ostream &out) const noexcept;

        private:
            struct Block
            {
                State state;
                char *value;
                std::uint32_t size;
            };

            std::vector<Block> heap;

            char *deref(const Block &block, std::uint32_t offset,
                    std::uint32_t size) const;
    };
}

#endif
