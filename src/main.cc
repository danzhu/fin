#include <fstream>
#include <iostream>
#include "runtime.h"

void print(Fin::Runtime &rt, Fin::Stack &st)
{
    std::cout << st.pop<int32_t>() << std::endl;
}

void input(Fin::Runtime &rt, Fin::Stack &st)
{
    int32_t val;
    std::cin >> val;
    st.push(val);
}

int main(int argc, const char *argv[])
{
    if (argc < 2)
    {
        std::cerr << "no input file" << std::endl;
        return 1;
    }

    std::ifstream src{argv[1]};

    if (!src)
    {
        std::cerr << "cannot open file" << std::endl;
        return 1;
    }

    Fin::Runtime runtime;

    auto &fin = runtime.createModule("fin");
    fin.addFunction("print(Int)", Fin::Function{print});
    fin.addFunction("input()Int", Fin::Function{input});

    try
    {
        runtime.run(src);
    }
    catch (const std::runtime_error &ex)
    {
        std::cerr << "Error: " << ex.what() << std::endl;
        runtime.backtrace(std::cerr);
        return 1;
    }

    return 0;
}
