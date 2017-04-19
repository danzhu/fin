#include "allocator.h"

Fin::Allocator::Allocator() {}

Fin::Allocator::~Allocator()
{
    // cleanup any blocks still in-use
    for (auto val : heap)
    {
        delete[] val;
    }
}

Fin::Ptr Fin::Allocator::alloc(uint32_t size)
{
    // TODO: reuse deallocated ptrs
    Ptr ptr = heap.size();
    heap.emplace_back(new char[size]);
    return ptr;
}

void Fin::Allocator::dealloc(Ptr ptr)
{
    auto &val = heap.at(ptr);
    delete[] val;
    val = nullptr;
}
