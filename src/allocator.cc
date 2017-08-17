#include "allocator.h"

#include <cassert>
#include "util.h"

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

Fin::Ptr Fin::Allocator::add(char *addr, Offset size, State state)
{
    assert(state != State::Freed);

#ifndef FIN_PEDANTIC
    // recycle if possible
    if (freeStore.size() > 0)
    {
        Ptr ptr{freeStore.top(), Offset{0}};
        freeStore.pop();

        assert(ptr.block < heap.size());
        auto &block = heap[ptr.block];

        assert(block.state == State::Freed);
        block = Block{addr, size, state};

        return ptr;
    }
#endif

    // no more freed blocks / pedantic, add new
    Ptr ptr{static_cast<std::uint32_t>(heap.size()), Offset{0}};
    heap.emplace_back(Block{addr, size, state});

    return ptr;
}

void Fin::Allocator::update(Ptr ptr, char *addr, Offset size)
{
    auto &block = heap.at(ptr.block);

    assert(block.state != State::Freed);
    block.value = addr;
    block.size = size;
}

void Fin::Allocator::remove(Ptr ptr)
{
    auto &block = heap.at(ptr.block);

    assert(block.state != State::Freed);
    remove(ptr.block, block);
}

Fin::Ptr Fin::Allocator::alloc(Offset size)
{
    auto addr = static_cast<char *>(std::malloc(size.value));
    if (!addr)
        throw std::runtime_error{"failed to allocate"};

    return add(addr, size, State::Managed);
}

Fin::Ptr Fin::Allocator::realloc(Ptr ptr, Offset size)
{
#ifdef FIN_PEDANTIC
    if (ptr.offset.value != 0)
        throw std::runtime_error{"internal reallocation"};
#endif

    auto &block = heap.at(ptr.block);

    if (block.state != State::Managed)
        throw std::runtime_error{"invalid reallocation"};

    auto addr = static_cast<char *>(std::realloc(block.value, size.value));
    if (!addr)
        throw std::runtime_error{"failed to reallocate"};

#ifdef FIN_PEDANTIC
    // track every reallocation so that access to old memory can be tracked
    remove(ptr.block, block);
    return add(addr, size, State::Managed);
#else
    block.value = addr;
    block.size = size;

    return ptr;
#endif
}

void Fin::Allocator::dealloc(Ptr ptr)
{
#ifdef FIN_PEDANTIC
    if (ptr.offset.value != 0)
        throw std::runtime_error{"internal deallocation"};
#endif

    auto &block = heap.at(ptr.block);

    if (block.state != State::Managed)
        throw std::runtime_error{"invalid deallocation"};

    std::free(block.value);
    remove(ptr.block, block);
}

char *Fin::Allocator::read(Ptr ptr, Offset size)
{
    LOG(2) << std::endl << "  & " << ptr;

    const auto &block = heap.at(ptr.block);
    return deref(block, ptr.offset, size);
}

char *Fin::Allocator::write(Ptr ptr, Offset size)
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
                nativeMem += block.size.value;
                break;

            case State::Managed:
                ++inUse;
                inUseMem += block.size.value;
                break;

            case State::Freed:
                ++freed;
                freedMem += block.size.value;
                break;
        }
    }

    out << "Allocator Summary:\n"
        << "  In use: " << inUseMem << " bytes in " << inUse << " blocks\n"
        << "   Freed: " << freedMem << " bytes in " << freed << " blocks\n"
        << "  Native: " << nativeMem << " bytes in " << native << " blocks\n"
        ;
}

void Fin::Allocator::remove(std::uint32_t idx, Block &block)
{
    assert(block.state != State::Freed);

    block.state = State::Freed;

#ifndef FIN_PEDANTIC
    freeStore.emplace(idx);
#endif
}

char *Fin::Allocator::deref(const Block &block, Offset offset,
        Offset size) const
{
    if (block.state == State::Freed)
        throw std::runtime_error{"invalid access to freed memory"};

    if (offset + size > block.size)
        throw std::runtime_error{"out-of-bound memory access at "
            + std::to_string((offset + size).value) + " out of "
            + std::to_string(block.size.value)};

    return &block.value[offset.value];
}
