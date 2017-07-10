#ifndef FIN_UTIL_H
#define FIN_UTIL_H

#include <stdexcept>
#include <vector>
#include "typedefs.h"

namespace Fin
{
    template<typename T> auto pop(T &col)
    {
        auto item = std::move(col.back());
        col.pop_back();
        return item;
    }

    template<typename T> std::vector<T> popRange(std::vector<T> &vec,
            std::size_t amount)
    {
        if (amount > vec.size())
            throw std::out_of_range{"not enough items "
                + std::to_string(vec.size())
                    + " / " + std::to_string(amount)};

        auto begin = vec.end() - amount;
        auto end = vec.end();

        std::vector<T> ret{std::make_move_iterator(begin),
            std::make_move_iterator(end)};
        vec.erase(begin, end);
        return ret;
    }

    constexpr Size alignTo(Size size, std::size_t align)
    {
        return static_cast<Size>((size & ~(align - 1))
                + (size % align ? align : 0));
    }
}

#endif
