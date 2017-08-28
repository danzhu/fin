#include "fin/allocator.h"

#include "fin/exception.h"
#include "fin/log.h"
#include "fin/typeinfo.h"
#include "fin/util.h"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <sstream>

Fin::Allocator::~Allocator() noexcept
{
    // cleanup any blocks still in-use
    for (const auto &block : _blocks)
    {
        std::free(block.memory._data);
    }
}

Fin::Ptr Fin::Allocator::alloc(Offset size, Access access)
{
    auto addr = static_cast<std::uint8_t *>(std::malloc(size._value));
    if (addr == nullptr)
        throw AllocationError{};

    auto ptr = add(Memory{addr}, size, access);

    LOG(2) << "\n  A " << ptr << " [" << size << "]";

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
    if (addr == nullptr)
        throw AllocationError{};

    LOG(2) << "\n  R " << ptr << " [" << size << "]";

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

    LOG(2) << "\n  D " << ptr;

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

std::string Fin::Allocator::summary() const noexcept
{
    std::ostringstream out{};

    int inUse = 0;
    std::size_t inUseMem = 0;
    int stack = 0;
    std::size_t stackMem = 0;
    int instr = 0;
    std::size_t instrMem = 0;
    int freed = 0;
    std::size_t freedMem = 0;

    for (const auto &block : _blocks)
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

    return out.str();
}

Fin::Allocator::Block &Fin::Allocator::getBlock(Ptr ptr)
{
    if (ptr._block >= _blocks.size())
        throw RuntimeError{"invalid ptr block"};
    return _blocks[ptr._block];
}

Fin::Ptr Fin::Allocator::add(Memory mem, Offset size, Access access)
{
#ifndef FIN_PEDANTIC
    // recycle if possible
    if (!_freeStore.empty())
    {
        Ptr ptr{_freeStore.top(), Offset{}};
        _freeStore.pop();

        assert(ptr._block < _blocks.size());
        auto &block = _blocks[ptr._block];

        assert(block.access == Access::None);
        assert(block.memory._data == nullptr);
        block = Block{mem, size, access};

        return ptr;
    }
#endif

    // no more freed blocks / pedantic, add new
    Ptr ptr{static_cast<std::uint32_t>(_blocks.size()), Offset{}};
    _blocks.emplace_back(Block{mem, size, access});

    return ptr;
}

void Fin::Allocator::remove(std::uint32_t idx)
{
    assert(idx < _blocks.size());
    // preserve size so that statistics are correct
    _blocks[idx].memory = Memory{};
    _blocks[idx].access = Access::None;

#ifndef FIN_PEDANTIC
    _freeStore.emplace(idx);
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
