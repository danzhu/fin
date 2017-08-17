#ifndef FIN_ALLOCATOR_H
#define FIN_ALLOCATOR_H

#include <cstdint>
#include <iostream>
#include <stack>
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

            Ptr add(char *addr, Offset size, State state = State::Native);
            void update(Ptr ptr, char *addr, Offset size);
            void remove(Ptr ptr);
            Ptr alloc(Offset size);
            Ptr realloc(Ptr ptr, Offset size);
            void dealloc(Ptr ptr);
            char *read(Ptr ptr, Offset size);
            char *write(Ptr ptr, Offset size);
            void summary(std::ostream &out) const noexcept;

        private:
            struct Block
            {
                char *value;
                Offset size;
                State state;
            };

            std::vector<Block> heap;

#ifndef FIN_PEDANTIC
            std::stack<std::uint32_t> freeStore;
#endif

            Ptr add(Block block);
            void remove(std::uint32_t idx, Block &block);
            char *deref(const Block &block, Offset offset, Offset size) const;
    };
}

#endif
