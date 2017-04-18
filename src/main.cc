#include <fstream>
#include <iostream>
#include "runtime.h"

void write(Fin::Runtime &rt, Fin::Stack &st)
{
    std::cout << st.pop<int32_t>() << std::endl;
}

void read(Fin::Runtime &rt, Fin::Stack &st)
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

    std::ifstream input{argv[1]};

    if (!input)
    {
        std::cerr << "cannot open file" << std::endl;
        return 1;
    }

    Fin::Runtime runtime;

    auto &io = runtime.createModule("io");
    io.addMethod("write", Fin::Method{write});
    io.addMethod("read", Fin::Method{read});

    runtime.run(input);

    return 0;
}
