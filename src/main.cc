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
} // end of anonymous namespace

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
    fin.addFunction("print(Int)", Fin::wrap(&print<Fin::Int>));
    fin.addFunction("print(Float)", Fin::wrap(&print<Fin::Float>));
    fin.addFunction("print(Bool)", Fin::wrap(&print<Fin::Bool>));
    fin.addFunction("input()Int", Fin::wrap(&input<Fin::Int>));
    fin.addFunction("input()Float", Fin::wrap(&input<Fin::Float>));
    fin.addFunction("input()Bool", Fin::wrap(&input<Fin::Bool>));
    fin.addFunction("alloc(Int)&[0]", Fin::wrap(&alloc), Fin::Index{1});
    fin.addFunction("realloc(&[0],Int)&[0]", Fin::wrap(&_realloc),
                    Fin::Index{1});
    fin.addFunction("dealloc(&0)", Fin::wrap(&dealloc), Fin::Index{1});
    fin.addFunction("write(Int)", Fin::wrap(&write));
    fin.addFunction("read()Int", Fin::wrap(&read));
    fin.addFunction("backtrace()", Fin::wrap(&backtrace));

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
