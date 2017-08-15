#include "allocator.h"

Fin::Allocator::Allocator() {}

Fin::Allocator::~Allocator() noexcept
{
    // cleanup any blocks still in-use
    for (const auto &val : heap)
    {
        if (val.state == State::Allocated)
            std::free(val.value);
    }
}

Fin::Ptr Fin::Allocator::alloc(std::uint32_t size)
{
    // TODO: reuse deallocated ptrs
    Ptr ptr{static_cast<std::uint32_t>(heap.size()), 0};
    auto addr = static_cast<char *>(std::malloc(size));

    if (!addr)
        throw std::runtime_error{"failed to allocate"};

    heap.emplace_back(Block{State::Allocated, addr, size});
    return ptr;
}

Fin::Ptr Fin::Allocator::add(char *addr, std::uint32_t size)
{
    Ptr ptr{static_cast<std::uint32_t>(heap.size()), 0};
    heap.emplace_back(Block{State::Native, addr, size});
    return ptr;
}

void Fin::Allocator::dealloc(Ptr ptr)
{
    auto &val = heap.at(ptr.block);

    if (val.state != State::Allocated)
        throw std::runtime_error{"invalid deallocation"};

    std::free(val.value);
    val.state = State::Freed;
}

Fin::Ptr Fin::Allocator::realloc(Ptr ptr, uint32_t size)
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

void Fin::Allocator::remove(Ptr ptr)
{
    auto &val = heap.at(ptr.block);

    val.state = State::Freed;
}

char *Fin::Allocator::read(Ptr ptr, std::uint32_t size) const
{
    LOG(2) << std::endl << "  & " << ptr;

    return deref(ptr.block, ptr.offset, size);
}

char *Fin::Allocator::write(Ptr ptr, std::uint32_t size)
{
    LOG(2) << std::endl << "  * " << ptr;

    return deref(ptr.block, ptr.offset, size);
}

void Fin::Allocator::summary(std::ostream &out) const noexcept
{
    int inUse = 0;
    std::size_t inUseMem = 0;
    int freed = 0;
    std::size_t freedMem = 0;
    int native = 0;
    std::size_t nativeMem = 0;

    for (const auto &val : heap)
    {
        switch (val.state)
        {
            case State::Allocated:
                ++inUse;
                inUseMem += val.size;
                break;

            case State::Freed:
                ++freed;
                freedMem += val.size;
                break;

            case State::Native:
                ++native;
                nativeMem += val.size;
                break;
        }
    }

    out << "Allocator Summary:\n"
        << "  In use: " << inUseMem << " bytes in " << inUse << " blocks\n"
        << "   Freed: " << freedMem << " bytes in " << freed << " blocks\n"
        << "  Native: " << nativeMem << " bytes in " << native << " blocks\n"
        ;
}

char *Fin::Allocator::deref(std::uint32_t blk, std::uint32_t offset,
        std::uint32_t size) const
{
    auto block = heap.at(blk);
    if (block.state == State::Freed || offset + size > block.size)
        throw std::runtime_error{"invalid memory access at "
            + std::to_string(offset + size) + " out of "
            + std::to_string(block.size)};
    return block.value + offset;
}
