#ifndef FIN_ARRAY_H
#define FIN_ARRAY_H

#include <cstdint>
#include <stdexcept>

namespace Fin
{
    template<typename T> class Array
    {
        T *_content;
        uint32_t _size;
    public:
        explicit Array(uint32_t size): _content{new T[size]}, _size{size} {}
        Array(const Array &other) = delete;
        ~Array()
        {
            delete[] _content;
        }

        Array &operator=(const Array &other) = delete;

        uint32_t size() const noexcept { return _size; }

        T &at(uint32_t idx)
        {
            if (idx >= _size)
                throw std::range_error{"out of range"};
            return _content[idx];
        }
    };
}

#endif
