#include <fstream>
#include <iostream>
#include "runtime.h"

template<typename T>
void print(Fin::Runtime &rt, Fin::Stack &st)
{
    std::cout << st.pop<T>() << std::endl;
}

template<typename T>
void input(Fin::Runtime &rt, Fin::Stack &st)
{
    T val;
    std::cin >> val;
    st.push(val);
}

void backtrace(Fin::Runtime &rt, Fin::Stack &st)
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

    Fin::Runtime runtime;

    auto &fin = runtime.createModule("fin");
    fin.addFunction("print(Int)", Fin::Function{print<int32_t>});
    fin.addFunction("print(Float)", Fin::Function{print<float>});
    fin.addFunction("print(Bool)", Fin::Function{print<bool>});
    fin.addFunction("input()Int", Fin::Function{input<int32_t>});
    fin.addFunction("input()Float", Fin::Function{input<float>});
    fin.addFunction("input()Bool", Fin::Function{input<bool>});
    fin.addFunction("backtrace()", Fin::Function{backtrace});

    try
    {
        runtime.run(src);
    }
    catch (const std::exception &ex)
    {
        std::cerr << "Error: " << ex.what() << std::endl;
        runtime.backtrace(std::cerr);
        return 1;
    }

    return 0;
}
