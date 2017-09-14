#include "fin/library.h"
#include "fin/runtime.h"
#include <fstream>
#include <iostream>

namespace
{
template <typename T>
void print(T val)
{
    std::cout << val << '\n';
}

template <typename T>
T input()
{
    T val;
    std::cin >> val;
    return val;
}

Fin::Ptr alloc(Fin::Allocator &alloc, Fin::TypeInfo type, Fin::Int len)
{
    auto size = type.alignedSize() * len;
    return alloc.alloc(size,
                       Fin::Allocator::Access::Read |
                               Fin::Allocator::Access::Write |
                               Fin::Allocator::Access::Free);
}

Fin::Ptr _realloc(Fin::Allocator &alloc, Fin::TypeInfo type, Fin::Ptr ptr,
                  Fin::Int len)
{
    auto size = type.size().align(type.alignment()) * len;
    return alloc.realloc(ptr, size);
}

void dealloc(Fin::Allocator &alloc, Fin::TypeInfo type, Fin::Ptr ptr)
{
    alloc.dealloc(ptr);
}

void write(Fin::Int val) { std::cout.put(static_cast<char>(val)); }

Fin::Int read() { return static_cast<Fin::Int>(std::cin.get()); }

void backtrace(Fin::Runtime &rt) { std::cout << rt.backtrace(); }
} // end of anonymous namespace

void _assert(Fin::Bool cond)
{
    if (!cond)
        throw std::runtime_error{"assertion failed"};
}

int main(int argc, const char *argv[])
{
    if (argc < 2)
    {
        std::cerr << "no input file\n";
        return 1;
    }

    std::ifstream src{argv[1], std::ios::binary};

    if (!src)
    {
        std::cerr << "cannot open file\n";
        return 1;
    }

    Fin::Runtime runtime{};

    auto &fin = runtime.createLibrary(Fin::LibraryID{"rt"});
    fin.addNative("print(Int)Void", print<Fin::Int>);
    fin.addNative("print(Float)Void", print<Fin::Float>);
    fin.addNative("print(Bool)Void", print<Fin::Bool>);
    fin.addNative("input()Int", input<Fin::Int>);
    fin.addNative("input()Float", input<Fin::Float>);
    fin.addNative("input()Bool", input<Fin::Bool>);
    fin.addNative("alloc(Int)&[0]", alloc);
    fin.addNative("realloc(&[0],Int)&[0]", _realloc);
    fin.addNative("dealloc(&0)Void", dealloc);
    fin.addNative("write(Int)", write);
    fin.addNative("read()Int", read);
    fin.addNative("backtrace()Void", backtrace);
    fin.addNative("assert(Bool)Void", _assert);

    try
    {
        runtime.load(src);
        runtime.run();
    }
    catch (const std::exception &ex)
    {
        std::cerr << "\nError: " << ex.what() << '\n'
                  << runtime.backtrace() << runtime.allocator().summary();
        return 1;
    }

    return 0;
}
