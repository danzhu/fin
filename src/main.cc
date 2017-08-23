#include "runtime.h"
#include "wrapper.h"
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

Fin::Ptr alloc(Fin::Allocator *alloc, Fin::TypeInfo type, Fin::Int len)
{
    auto size = type.alignedSize() * len;
    return alloc->alloc(size,
                        Fin::Allocator::Access::Read |
                                Fin::Allocator::Access::Write |
                                Fin::Allocator::Access::Free);
}

Fin::Ptr _realloc(Fin::Allocator *alloc, Fin::TypeInfo type, Fin::Ptr ptr,
                  Fin::Int len)
{
    auto size = type.size().align(type.alignment()) * len;
    return alloc->realloc(ptr, size);
}

void dealloc(Fin::Allocator *alloc, Fin::Ptr ptr) { alloc->dealloc(ptr); }

void write(Fin::Int val) { std::cout.put(static_cast<char>(val)); }

Fin::Int read() { return static_cast<Fin::Int>(std::cin.get()); }

void backtrace(Fin::Runtime *rt) { rt->backtrace(std::cout); }
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
    fin.addFunction(Fin::wrap("print(Int)", &print<Fin::Int>));
    fin.addFunction(Fin::wrap("print(Float)", &print<Fin::Float>));
    fin.addFunction(Fin::wrap("print(Bool)", &print<Fin::Bool>));
    fin.addFunction(Fin::wrap("input()Int", &input<Fin::Int>));
    fin.addFunction(Fin::wrap("input()Float", &input<Fin::Float>));
    fin.addFunction(Fin::wrap("input()Bool", &input<Fin::Bool>));
    fin.addFunction(Fin::wrap("alloc(Int)&[0]", &alloc, 1));
    fin.addFunction(Fin::wrap("realloc(&[0],Int)&[0]", &_realloc, 1));
    fin.addFunction(Fin::wrap("dealloc(&0)", &dealloc, 1));
    fin.addFunction(Fin::wrap("write(Int)", &write));
    fin.addFunction(Fin::wrap("read()Int", &read));
    fin.addFunction(Fin::wrap("backtrace()", &backtrace));

    try
    {
        runtime.load(src);
        runtime.run();
    }
    catch (const std::exception &ex)
    {
        std::cerr << "\nError: " << ex.what() << '\n';
        runtime.backtrace(std::cerr);
        runtime.allocator().summary(std::cerr);
        return 1;
    }

#if FIN_DEBUG > 0
    runtime.allocator().summary(std::cerr);
#endif

    return 0;
}
