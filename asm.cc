#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>

std::map<std::string, char> readOpcodes(const std::string &filename)
{
    std::map<std::string, char> opcodes;
    std::ifstream op{filename};

    std::string line;
    char opcode = 0;

    while (std::getline(op, line))
        opcodes.emplace(line.substr(0, line.size() - 1), opcode++);

    return opcodes;
}

int main()
{
    auto opcodes = readOpcodes("src/opcodes");

    std::string op;
    while (std::cin >> op)
    {
        auto it = opcodes.find(op);
        if (it != opcodes.end())
        {
            std::cout << it->second;
        }
        else
        {
            std::istringstream ss{op};
            int32_t val;
            ss >> val;

            std::cout
                << static_cast<char>(val)
                << static_cast<char>(val >> 8)
                << static_cast<char>(val >> 16)
                << static_cast<char>(val >> 24)
                ;
        }
    }

    if (!std::cin.eof())
    {
        std::cerr << "not completed" << std::endl;
        return 1;
    }
}
