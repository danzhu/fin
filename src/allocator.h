#ifndef FIN_ALLOCATOR_H
#define FIN_ALLOCATOR_H

#include "memory.h"
#include "typedefs.h"
#include <cstdint>
#include <iostream>
#include <stack>
#include <string>
#include <vector>

namespace Fin
{
class Memory;
class TypeInfo;

class Allocator
{
public:
    enum class Access
    {
        None = 0,
        Read = 1 << 0,
        Write = 1 << 1,
        Free = 1 << 2,
    };

    Allocator() noexcept = default;
    ~Allocator() noexcept;

    Allocator(const Allocator &other) = delete;
    Allocator(Allocator &&other) = delete;

    Allocator &operator=(const Allocator &other) = delete;
    Allocator &operator=(Allocator &&other) = delete;

    Ptr alloc(Offset size, Access access);
    Ptr realloc(Ptr ptr, Offset size);
    void dealloc(Ptr ptr);
    Memory readSize(Ptr ptr, TypeInfo type);
    Memory writeSize(Ptr ptr, TypeInfo type);
    Memory get(Ptr ptr);
    void setSize(Ptr ptr, Offset size);
    void summary(std::ostream &out) const noexcept;

    template <typename T>
    T read(Ptr ptr)
    {
        constexpr auto size = Offset{sizeof(T)};

        LOG(2) << "\n  & " << ptr;

        const auto &block = getBlock(ptr);

        checkOffset(block, ptr._offset, size);
        checkAccess(block, Access::Read);
        return Memory{block.memory + ptr._offset}.as<T>();
    }

    template <typename T>
    void write(Ptr ptr, T val)
    {
        constexpr auto size = Offset{sizeof(T)};

        LOG(2) << "\n  * " << ptr;

        const auto &block = getBlock(ptr);

        checkOffset(block, ptr._offset, size);
        checkAccess(block, Access::Write);
        Memory{block.memory + ptr._offset}.as<T>() = val;
    }

private:
    struct Block
    {
        Memory memory;
        Offset size;
        Access access{Access::None};
    };

    std::vector<Block> heap;

#ifndef FIN_PEDANTIC
    std::stack<std::uint32_t> freeStore;
#endif

    Block &getBlock(Ptr ptr);
    Ptr add(Memory mem, Offset size, Access access);
    void remove(std::uint32_t idx);
    void checkOffset(const Block &block, Offset off, Offset size) const;
    void checkAccess(const Block &block, Access access) const;
};
} // namespace Fin

#endif
