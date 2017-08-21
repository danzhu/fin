#ifndef FIN_UTIL_H
#define FIN_UTIL_H

#define PLURAL(num,str) num << ' ' << str << (num == 1 ? "" : "s")

#include <stdexcept>
#include <vector>
#include "typedefs.h"

namespace Fin
{
    template<typename T>
    auto pop(T &col)
    {
        auto item = std::move(col.back());
        col.pop_back();
        return item;
    }

    template<typename T>
    std::vector<T> popRange(std::vector<T> &vec, std::size_t amount)
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

    template<typename T>
    constexpr std::enable_if_t<std::is_enum<T>::value, bool> hasFlag(
            T val, T flag)
    {
        return (val & flag) != static_cast<T>(0);
    }

    template<typename T>
    constexpr std::enable_if_t<std::is_enum<T>::value, T> operator&(
            T self, T other) noexcept
    {
        using U = std::underlying_type_t<T>;
        return static_cast<T>(static_cast<U>(self) & static_cast<U>(other));
    }

    template<typename T>
    constexpr std::enable_if_t<std::is_enum<T>::value, T> operator|(
            T self, T other) noexcept
    {
        using U = std::underlying_type_t<T>;
        return static_cast<T>(static_cast<U>(self) | static_cast<U>(other));
    }
}

#endif
