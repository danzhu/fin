#ifndef __ALLOCATOR_H__
#define __ALLOCATOR_H__

#include <cstdint>
#include <vector>

namespace Fin
{
    typedef uint32_t Ptr;

    class Allocator
    {
        std::vector<char *> heap;
    public:
        Allocator();
        ~Allocator();
        Ptr alloc(uint32_t size);
        void dealloc(Ptr ptr);

        template<typename T> T &deref(Ptr ptr, uint16_t offset = 0)
        {
            return *reinterpret_cast<T *>(heap.at(ptr) + offset);
        }
    };
}

#endif
