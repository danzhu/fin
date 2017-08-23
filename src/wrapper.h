#ifndef FIN_WRAPPER_H
#define FIN_WRAPPER_H

#include "contract.h"
#include "function.h"
#include "runtime.h"
#include "stack.h"
#include "traits.h"
#include "typeinfo.h"

namespace Fin
{
namespace detail
{
struct State
{
    Index typeInfo;
    Index contract;
};

template <typename T, typename Enable = std::true_type>
struct Read;

template <typename T>
struct Read<T, typename TypeTraits<T>::IsPrimitive>
{
    static T read(Runtime &rt, Contract &ctr, State &state)
    {
        return rt.stack().pop<T>();
    }
};

template <>
struct Read<Runtime *>
{
    static Runtime *read(Runtime &rt, Contract &ctr, State &state)
    {
        return &rt;
    }
};

template <>
struct Read<Allocator *>
{
    static Allocator *read(Runtime &rt, Contract &ctr, State &state)
    {
        return &rt.allocator();
    }
};

template <>
struct Read<TypeInfo>
{
    static TypeInfo read(Runtime &rt, Contract &ctr, State &state)
    {
        return ctr.size(--state.typeInfo);
    }
};

template <typename T, typename Enable = std::true_type>
struct Write;

template <typename T>
struct Write<T, typename TypeTraits<T>::IsPrimitive>
{
    static void write(Stack &stack, T val) { stack.push(val); }
};

template <typename Fn, typename Tuple, std::size_t... Is>
decltype(auto) applyArgs(Fn fn, const Tuple &tup, std::index_sequence<Is...>)
{
    return (*fn)(std::get<Is>(tup)...);
}

template <typename Fn, typename... Args>
decltype(auto) applyArgs(Fn fn, const std::tuple<Args...> &tup)
{
    auto idcs = std::make_index_sequence<sizeof...(Args)>();
    return applyArgs(fn, tup, idcs);
}

template <typename... Args>
struct ArgCreator;

template <>
struct ArgCreator<>
{
    static std::tuple<> createArgs(Runtime &rt, Contract &ctr, State &state)
    {
        return std::make_tuple();
    }
};

template <typename T, typename... Args>
struct ArgCreator<T, Args...>
{
    static std::tuple<T, Args...> createArgs(Runtime &rt, Contract &ctr,
                                             State &state)
    {
        auto args = ArgCreator<Args...>::createArgs(rt, ctr, state);
        auto arg = std::make_tuple(detail::Read<T>::read(rt, ctr, state));
        return std::tuple_cat(arg, args);
    }
};

template <typename... Args>
std::tuple<Args...> createArgs(Runtime &rt, Contract &ctr)
{
    State state{static_cast<Index>(ctr.sizes()),
                static_cast<Index>(ctr.contracts())};

    return ArgCreator<Args...>::createArgs(rt, ctr, state);

    // TODO: static assert that state is either ignored or all used,
    // this will require state to be template / constexpr
}
} // namespace detail

template <typename Ret, typename... Args>
class Wrapper
{
public:
    explicit Wrapper(Ret (*fn)(Args...)) noexcept : _fn{fn} {}

    void operator()(Runtime &rt, Contract &ctr) const
    {
        auto args = detail::createArgs<Args...>(rt, ctr);
        auto res = detail::applyArgs(_fn, args);
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
        auto args = detail::createArgs<Args...>(rt, ctr);
        detail::applyArgs(_fn, args);
    }

private:
    void (*_fn)(Args...);
};

template <typename Ret, typename... Args>
NativeFunction wrap(Ret (*fn)(Args...)) noexcept
{
    // TODO: acquire gens and ctrs from function signature
    return Wrapper<Ret, Args...>{fn};
}
} // namespace Fin

#endif
