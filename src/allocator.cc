#include "allocator.h"

#include <cassert>

Fin::Allocator::Allocator() {}

Fin::Allocator::~Allocator() noexcept
{
    // cleanup any blocks still in-use
    for (const auto &block : heap)
    {
        if (block.state == State::Managed)
            std::free(block.value);
    }
}

Fin::Ptr Fin::Allocator::alloc(std::uint32_t size, State state)
{
    // TODO: reuse deallocated ptrs
    auto addr = static_cast<char *>(std::malloc(size));
    if (!addr)
        throw std::runtime_error{"failed to allocate"};

    return add(addr, size, state);
}

Fin::Ptr Fin::Allocator::add(char *addr, std::uint32_t size, State state)
{
    assert(state != State::Freed);

    Ptr ptr{static_cast<std::uint32_t>(heap.size()), 0};
    heap.emplace_back(Block{state, addr, size});
    return ptr;
}

void Fin::Allocator::remove(Ptr ptr)
{
    auto &block = heap.at(ptr.block);

    block.state = State::Freed;
}

void Fin::Allocator::dealloc(Ptr ptr)
{
    auto &block = heap.at(ptr.block);

    if (block.state != State::Managed)
        throw std::runtime_error{"invalid deallocation"};

    std::free(block.value);
    block.state = State::Freed;
}

Fin::Ptr Fin::Allocator::realloc(Ptr ptr, std::uint32_t size)
{
    auto &block = heap.at(ptr.block);

    if (block.state != State::Managed)
        throw std::runtime_error{"invalid reallocation"};

    block.value = static_cast<char *>(std::realloc(block.value, size));

    if (!block.value)
        throw std::runtime_error{"failed to reallocate"};

    block.size = size;

    return ptr;
}

char *Fin::Allocator::read(Ptr ptr, std::uint32_t size)
{
    LOG(2) << std::endl << "  & " << ptr;

    const auto &block = heap.at(ptr.block);
    return deref(block, ptr.offset, size);
}

char *Fin::Allocator::write(Ptr ptr, std::uint32_t size)
{
    LOG(2) << std::endl << "  * " << ptr;

    const auto &block = heap.at(ptr.block);

    if (block.state == State::ReadOnly)
        throw std::runtime_error{"invalid write to read-only memory"};

    return deref(block, ptr.offset, size);
}

void Fin::Allocator::summary(std::ostream &out) const noexcept
{
    int inUse = 0;
    std::size_t inUseMem = 0;
    int freed = 0;
    std::size_t freedMem = 0;
    int native = 0;
    std::size_t nativeMem = 0;

    for (const auto &block : heap)
    {
        switch (block.state)
        {
            case State::ReadOnly:
                // ignore
                break;

            case State::Native:
                ++native;
                nativeMem += block.size;
                break;

            case State::Managed:
                ++inUse;
                inUseMem += block.size;
                break;

            case State::Freed:
                ++freed;
                freedMem += block.size;
                break;
        }
    }

    out << "Allocator Summary:\n"
        << "  In use: " << inUseMem << " bytes in " << inUse << " blocks\n"
        << "   Freed: " << freedMem << " bytes in " << freed << " blocks\n"
        << "  Native: " << nativeMem << " bytes in " << native << " blocks\n"
        ;
}

char *Fin::Allocator::deref(const Block &block, std::uint32_t offset,
        std::uint32_t size) const
{
    if (block.state == State::Freed)
        throw std::runtime_error{"invalid access to freed memory"};

    if (offset + size > block.size)
        throw std::runtime_error{"out-of-bound memory access at "
            + std::to_string(offset + size) + " out of "
            + std::to_string(block.size)};

    return &block.value[offset];
}
