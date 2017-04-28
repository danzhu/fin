#include "allocator.h"

Fin::Allocator::Allocator() {}

Fin::Allocator::~Allocator()
{
    // cleanup any blocks still in-use
    for (auto val : heap)
    {
        if (val.state == State::Allocated)
            delete[] val.value;
    }
}

Fin::Ptr Fin::Allocator::alloc(uint32_t size)
{
    // TODO: reuse deallocated ptrs
    Ptr ptr = heap.size() << OFFSET_WIDTH;
    heap.emplace_back(Block{State::Allocated, new char[size], size});
    return ptr;
}

Fin::Ptr Fin::Allocator::add(char *addr, uint32_t size)
{
    Ptr ptr = heap.size() << OFFSET_WIDTH;
    heap.emplace_back(Block{State::Native, addr, size});
    return ptr;
}

void Fin::Allocator::dealloc(Ptr ptr)
{
    auto &val = heap.at(ptr >> OFFSET_WIDTH);
    if (val.state != State::Allocated)
        throw std::runtime_error{"invalid free"};
    delete[] val.value;
    val.state = State::Freed;
}

void Fin::Allocator::remove(Ptr ptr)
{
    auto &val = heap.at(ptr >> OFFSET_WIDTH);
    val.state = State::Freed;
}
