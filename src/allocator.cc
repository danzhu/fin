#include "allocator.h"

#include "exception.h"
#include "log.h"
#include "util.h"
#include <cassert>

Fin::Allocator::Allocator() noexcept {}

Fin::Allocator::~Allocator() noexcept
{
    // cleanup any blocks still in-use
    for (const auto &block : heap)
    {
        std::free(block.memory._data);
    }
}

Fin::Ptr Fin::Allocator::alloc(Offset size, Access access)
{
    auto addr = static_cast<std::uint8_t *>(std::malloc(size._value));
    if (!addr)
        throw AllocationError{};

    auto ptr = add(Memory{addr}, size, access);

    LOG(1) << "\n  A " << ptr << " [" << size << "]";

    return ptr;
}

Fin::Ptr Fin::Allocator::realloc(Ptr ptr, Offset size)
{
#ifdef FIN_PEDANTIC
    if (ptr._offset._value != 0)
        throw RuntimeError{"internal reallocation"};
#endif

    auto &block = getBlock(ptr);

    checkAccess(block, Access::Free);

    auto addr = static_cast<std::uint8_t *>(
            std::realloc(block.memory._data, size._value));
    if (!addr)
        throw AllocationError{};

    LOG(1) << "\n  R " << ptr << " [" << size << "]";

#ifdef FIN_PEDANTIC
    // track every reallocation so that access to old memory can be tracked
    auto ret = add(Memory{addr}, size, block.access);
    remove(ptr._block);
    return ret;
#else
    block.memory = Memory{addr};
    block.size = size;

    return ptr;
#endif
}

void Fin::Allocator::dealloc(Ptr ptr)
{
#ifdef FIN_PEDANTIC
    if (ptr._offset._value != 0)
        throw RuntimeError{"internal deallocation"};
#endif

    auto &block = getBlock(ptr);

    checkAccess(block, Access::Free);

    LOG(1) << "\n  D " << ptr;

    std::free(block.memory._data);
    remove(ptr._block);
}

Fin::Memory Fin::Allocator::readSize(Ptr ptr, TypeInfo type)
{
    LOG(2) << "\n  & " << ptr;

    const auto &block = getBlock(ptr);

    checkOffset(block, ptr._offset, type.size());
    checkAccess(block, Access::Read);

    return block.memory + ptr._offset;
}

Fin::Memory Fin::Allocator::writeSize(Ptr ptr, TypeInfo type)
{
    LOG(2) << "\n  * " << ptr;

    const auto &block = getBlock(ptr);

    checkOffset(block, ptr._offset, type.size());
    checkAccess(block, Access::Write);

    return block.memory + ptr._offset;
}

Fin::Memory Fin::Allocator::get(Ptr ptr) { return getBlock(ptr).memory; }

void Fin::Allocator::setSize(Ptr ptr, Offset size)
{
    // FIXME: hacks
    getBlock(ptr).size = size;
}

void Fin::Allocator::summary(std::ostream &out) const noexcept
{
    int inUse = 0;
    std::size_t inUseMem = 0;
    int stack = 0;
    std::size_t stackMem = 0;
    int instr = 0;
    std::size_t instrMem = 0;
    int freed = 0;
    std::size_t freedMem = 0;

    for (const auto &block : heap)
    {
        // TODO: this makes assumptions on what they are used for,
        // maybe a better way to give summary?

        if (hasFlag(block.access, Access::Free))
        {
            ++inUse;
            inUseMem += block.size._value;
        }
        else if (hasFlag(block.access, Access::Write))
        {
            ++stack;
            stackMem += block.size._value;
        }
        else if (hasFlag(block.access, Access::Read))
        {
            ++instr;
            instrMem += block.size._value;
        }
        else
        {
            ++freed;
            freedMem += block.size._value;
        }
    }

    out << "Allocator Summary:\n"
        << "  In use: " << PLURAL(inUseMem, "byte") << " in "
        << PLURAL(inUse, "block") << "\n"
        << "   Stack: " << PLURAL(stackMem, "byte") << " in "
        << PLURAL(stack, "block") << "\n"
        << "   Instr: " << PLURAL(instrMem, "byte") << " in "
        << PLURAL(instr, "block") << "\n"
        << "  -------\n"
        << "   Freed: " << PLURAL(freedMem, "byte") << " in "
        << PLURAL(freed, "block") << "\n";
}

Fin::Allocator::Block &Fin::Allocator::getBlock(Ptr ptr)
{
    if (ptr._block >= heap.size())
        throw RuntimeError{"invalid ptr block"};
    return heap[ptr._block];
}

Fin::Ptr Fin::Allocator::add(Memory mem, Offset size, Access access)
{
#ifndef FIN_PEDANTIC
    // recycle if possible
    if (freeStore.size() > 0)
    {
        Ptr ptr{freeStore.top(), Offset{}};
        freeStore.pop();

        assert(ptr._block < heap.size());
        auto &block = heap[ptr._block];

        assert(block.access == Access::None);
        assert(block.memory._data == nullptr);
        block = Block{mem, size, access};

        return ptr;
    }
#endif

    // no more freed blocks / pedantic, add new
    Ptr ptr{static_cast<std::uint32_t>(heap.size()), Offset{}};
    heap.emplace_back(Block{mem, size, access});

    return ptr;
}

void Fin::Allocator::remove(std::uint32_t idx)
{
    assert(idx < heap.size());
    // preserve size so that statistics are correct
    heap[idx].memory = Memory{};
    heap[idx].access = Access::None;

#ifndef FIN_PEDANTIC
    freeStore.emplace(idx);
#endif
}

void Fin::Allocator::checkOffset(const Block &block, Offset off,
                                 Offset size) const
{
    if (off + size > block.size)
        throw RuntimeError{"access out of range"};
}

void Fin::Allocator::checkAccess(const Block &block, Access access) const
{
    if (!hasFlag(block.access, access))
        throw RuntimeError{"invalid permissions"};
}
