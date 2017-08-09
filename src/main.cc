#include <fstream>
#include <iostream>
#include "runtime.h"

template<typename T> void print(Fin::Runtime &rt, Fin::Contract &ctr,
        Fin::Stack &st)
{
    std::cout << st.pop<T>() << std::endl;
}

template<typename T> void input(Fin::Runtime &rt, Fin::Contract &ctr,
        Fin::Stack &st)
{
    T val;
    std::cin >> val;
    st.push(val);
}

void alloc(Fin::Runtime &rt, Fin::Contract &ctr, Fin::Stack &st)
{
    auto type = ctr.sizes.at(0);

    auto len = st.pop<Fin::Int>();

    auto size = Fin::alignTo(type.size, type.alignment) * len;
    auto ptr = rt.allocator().alloc(size);

    st.push(ptr);
}

void _realloc(Fin::Runtime &rt, Fin::Contract &ctr, Fin::Stack &st)
{
    auto type = ctr.sizes.at(0);

    auto len = st.pop<Fin::Int>();
    auto ptr = st.pop<Fin::Ptr>();

    auto size = Fin::alignTo(type.size, type.alignment) * len;
    ptr = rt.allocator().realloc(ptr, size);

    st.push(ptr);
}

void dealloc(Fin::Runtime &rt, Fin::Contract &ctr, Fin::Stack &st)
{
    auto ptr = st.pop<Fin::Ptr>();

    rt.allocator().dealloc(ptr);
}

void write(Fin::Runtime &rt, Fin::Contract &ctr, Fin::Stack &st)
{
    auto c = static_cast<char>(st.pop<Fin::Int>());
    std::cout.put(c);
}

void read(Fin::Runtime &rt, Fin::Contract &ctr, Fin::Stack &st)
{
    char c;
    std::cin.get(c);
    st.push(static_cast<Fin::Int>(c));
}

void backtrace(Fin::Runtime &rt, Fin::Contract &ctr, Fin::Stack &st)
{
    rt.backtrace(std::cout);
}

int main(int argc, const char *argv[])
{
    if (argc < 2)
    {
        std::cerr << "no input file" << std::endl;
        return 1;
    }

    std::ifstream src{argv[1], std::ios::binary};

    if (!src)
    {
        std::cerr << "cannot open file" << std::endl;
        return 1;
    }

    Fin::Runtime runtime{2048};

    auto &fin = runtime.createLibrary("rt");
    fin.addFunction(Fin::Function{"print(Int)", print<Fin::Int>});
    fin.addFunction(Fin::Function{"print(Float)", print<Fin::Float>});
    fin.addFunction(Fin::Function{"print(Bool)", print<Fin::Bool>});
    fin.addFunction(Fin::Function{"input()Int", input<Fin::Int>});
    fin.addFunction(Fin::Function{"input()Float", input<Fin::Float>});
    fin.addFunction(Fin::Function{"input()Bool", input<Fin::Bool>});
    fin.addFunction(Fin::Function{"alloc(Int)&[0]", alloc, 1});
    fin.addFunction(Fin::Function{"realloc(&[0],Int)&[0]", _realloc, 1});
    fin.addFunction(Fin::Function{"dealloc(&0)", dealloc, 1});
    fin.addFunction(Fin::Function{"write(Int)", write});
    fin.addFunction(Fin::Function{"read()Int", read});
    fin.addFunction(Fin::Function{"backtrace()", backtrace});

    try
    {
        runtime.load(src);
        runtime.run();
    }
    catch (const std::exception &ex)
    {
        std::cerr << "Error: " << ex.what() << std::endl;
        runtime.backtrace(std::cerr);
        return 1;
    }

    return 0;
}
