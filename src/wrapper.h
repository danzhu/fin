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
constexpr int ind = std::is_same<T, U>::value ? 1 : 0;

constexpr int sum() { return 0; }

template <typename T, typename... Args>
constexpr int sum(T val, Args... args)
{
    return val + sum(args...);
}

template <typename T, typename... Args>
constexpr int count = sum(ind<T, Args>...);

template <typename T, typename Enable = std::true_type>
struct Read;

template <typename T>
struct Read<T, typename TypeTraits<T>::IsPrimitive>
{
    template <int Size, int Ctr>
    static T read(Runtime &rt, Contract &ctr)
    {
        return rt.stack().pop<T>();
    }
};

template <>
struct Read<Runtime *>
{
    template <int Size, int Ctr>
    static Runtime *read(Runtime &rt, Contract &ctr)
    {
        return &rt;
    }
};

template <>
struct Read<Allocator *>
{
    template <int Size, int Ctr>
    static Allocator *read(Runtime &rt, Contract &ctr)
    {
        return &rt.allocator();
    }
};

template <>
struct Read<TypeInfo>
{
    template <int Size, int Ctr>
    static TypeInfo read(Runtime &rt, Contract &ctr)
    {
        return ctr.size(Size);
    }
};

template <typename T, typename Enable = std::true_type>
struct Write;

template <typename T>
struct Write<T, typename TypeTraits<T>::IsPrimitive>
{
    static void write(Stack &stack, T val) { stack.push(val); }
};

template <typename... Args>
struct ArgCreator;

template <>
struct ArgCreator<>
{
    template <int Size, int Ctr>
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
    template <int Size, int Ctr>
    static std::tuple<T, Args...> createArgs(Runtime &rt, Contract &ctr)
    {
        constexpr int sz = Size - ind<T, TypeInfo>;
        constexpr int ct = Ctr - ind<T, Contract>;

        auto args = ArgCreator<Args...>::template createArgs<sz, ct>(rt, ctr);
        auto arg = std::make_tuple(
                detail::Read<T>::template read<sz, ct>(rt, ctr));
        return std::tuple_cat(arg, args);
    }
};

template <typename... Args>
std::tuple<Args...> createArgs(Runtime &rt, Contract &ctr)
{
    constexpr int sz = count<TypeInfo, Args...>;
    constexpr int ct = count<Contract, Args...>;

    return ArgCreator<Args...>::template createArgs<sz, ct>(rt, ctr);
}

template <typename Fn, typename Tuple, std::size_t... Is>
decltype(auto) applyArgs(Fn fn, const Tuple &tup, std::index_sequence<Is...>)
{
    return (*fn)(std::get<Is>(tup)...);
}

template <typename Ret, typename... Args>
decltype(auto) invoke(Ret (*fn)(Args...), Runtime &rt, Contract &ctr)
{
    auto args = createArgs<Args...>(rt, ctr);
    auto idcs = std::make_index_sequence<sizeof...(Args)>();
    return applyArgs(fn, args, idcs);
}
} // namespace detail

template <typename Ret, typename... Args>
class Wrapper
{
public:
    explicit Wrapper(Ret (*fn)(Args...)) noexcept : _fn{fn} {}

    void operator()(Runtime &rt, Contract &ctr) const
    {
        auto res = detail::invoke(_fn, rt, ctr);
        detail::Write<Ret>::write(rt.stack(), res);
    }

private:
    Ret (*_fn)(Args...);
};

template <typename... Args>
class Wrapper<void, Args...>
{
public:
    explicit Wrapper(void (*fn)(Args...)) noexcept : _fn{fn} {}

    void operator()(Runtime &rt, Contract &ctr) const
    {
        detail::invoke(_fn, rt, ctr);
    }

private:
    void (*_fn)(Args...);
};
} // namespace Fin

#endif
