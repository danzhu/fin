#ifndef FIN_WRAPPER_H
#define FIN_WRAPPER_H

#include "contract.h"
#include "function.h"
#include "runtime.h"
#include "stack.h"
#include "traits.h"
#include "typeinfo.h"
#include <algorithm>

namespace Fin
{
namespace detail
{
template <typename T, typename U>
constexpr Index ind = std::is_same<T, U>::value ? 1 : 0;

template <typename Tar>
constexpr Index count() noexcept
{
    return 0;
}

template <typename Tar, typename T, typename... Args>
constexpr Index count() noexcept
{
    return detail::ind<T, Tar> + detail::count<Tar, Args...>();
}

template <typename T, typename Enable = std::true_type>
struct Read
{
    static_assert(sizeof(T) == -1, "unsupported argument type");
};

template <typename T>
struct Read<T, typename IsPrimitive<T>::type>
{
    template <Index Size, Index Ctr>
    static T read(Runtime &rt, Contract &ctr)
    {
        return rt.stack().pop<T>();
    }
};

template <>
struct Read<Runtime &>
{
    template <Index Size, Index Ctr>
    static Runtime &read(Runtime &rt, Contract &ctr)
    {
        return rt;
    }
};

template <>
struct Read<Allocator &>
{
    template <Index Size, Index Ctr>
    static Allocator &read(Runtime &rt, Contract &ctr)
    {
        return rt.allocator();
    }
};

template <>
struct Read<TypeInfo>
{
    template <Index Size, Index Ctr>
    static TypeInfo read(Runtime &rt, Contract &ctr)
    {
        return ctr.size(Size);
    }
};

template <>
struct Read<Contract &>
{
    template <Index Size, Index Ctr>
    static Contract &read(Runtime &rt, Contract &ctr)
    {
        return ctr.contract(Ctr);
    }
};

template <typename T, typename Enable = std::true_type>
struct Write
{
    static_assert(sizeof(T) == -1, "unsupported return type");
};

template <typename T>
struct Write<T, typename IsPrimitive<T>::type>
{
    static void write(Stack &stack, T val) { stack.push(val); }
};

template <typename... Args>
struct ArgCreator;

template <>
struct ArgCreator<>
{
    template <Index Size, Index Ctr>
    static std::tuple<> createArgs(Runtime &rt, Contract &ctr)
    {
        static_assert(Size == 0, "size is not 0");
        static_assert(Ctr == 0, "contract is not 0");

        return std::make_tuple();
    }
};

template <typename T, typename... Args>
struct ArgCreator<T, Args...>
{
    template <Index Size, Index Ctr>
    static std::tuple<T, Args...> createArgs(Runtime &rt, Contract &ctr)
    {
        constexpr auto sz = Size - detail::ind<T, TypeInfo>;
        constexpr auto ct = Ctr - detail::ind<T, Contract>;

        auto args = ArgCreator<Args...>::template createArgs<sz, ct>(rt, ctr);

        std::tuple<T> arg{Read<T>::template read<sz, ct>(rt, ctr)};

        return std::tuple_cat(arg, args);
    }
};

template <typename Fn, typename Tuple, std::size_t... Is>
decltype(auto) applyArgs(Fn fn, Tuple tup, std::index_sequence<Is...>)
{
    (void)tup;
    return (*fn)(std::get<Is>(tup)...);
}

template <typename Ret, typename... Args>
Ret invoke(Ret (*fn)(Args...), Runtime &rt, Contract &ctr, std::true_type)
{
    constexpr auto sz = detail::count<TypeInfo, Args...>();
    constexpr auto ct = detail::count<Contract, Args...>();

    auto args = ArgCreator<Args...>::template createArgs<sz, ct>(rt, ctr);
    auto idcs = std::make_index_sequence<sizeof...(Args)>();
    return detail::applyArgs(fn, std::move(args), idcs);
}

template <typename Ret, typename... Args>
void invoke(Ret (*fn)(Args...), Runtime &rt, Contract &ctr, std::false_type)
{
    auto ret = detail::invoke(fn, rt, ctr, std::true_type{});
    Write<Ret>::write(rt.stack(), std::move(ret));
}
} // namespace detail

template <typename Ret, typename... Args>
class Wrapper
{
public:
    explicit Wrapper(Ret (*fn)(Args...)) noexcept : _fn{fn} {}

    void operator()(Runtime &rt, Contract &ctr) const
    {
        detail::invoke(_fn, rt, ctr, std::is_void<Ret>{});
    }

private:
    Ret (*_fn)(Args...);
};
} // namespace Fin

#endif
