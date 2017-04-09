#include <fstream>
#include <iostream>
#include "runtime.h"

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
    runtime.run(input);

    return 0;
}
