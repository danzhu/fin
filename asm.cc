#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include "src/opcode.h"

std::map<std::string, char> readOpcodes()
{
    std::map<std::string, char> opcodes;

    std::size_t size = sizeof(Fin::OpcodeNames) / sizeof(*Fin::OpcodeNames);
    for (std::size_t opcode = 0; opcode < size; ++opcode)
    {
        std::string name = Fin::OpcodeNames[opcode];
        opcodes.emplace(name, opcode);
    }

    return opcodes;
}

template<typename T>
void print(T val)
{
    auto size = sizeof(T) / sizeof(char);
    for (unsigned int i = 0; i < size; ++i)
        std::cout << static_cast<char>(val >> (i * 8));
}

template<typename T>
void encode(const std::string &src)
{
    std::istringstream ss{src};
    T val;
    ss >> val;

    print(val);
}

int main()
{
    auto opcodes = readOpcodes();

    std::string line;
    while (std::getline(std::cin, line))
    {
        if (line.empty() || line[0] == '#')
            continue;

        std::istringstream ss{line};

        // opcode
        std::string op;
        ss >> op;

        auto it = opcodes.find(op);
        if (it == opcodes.end())
        {
            std::cerr << "no opcode '" << op << "'" << std::endl;
            return 1;
        }
        std::cout << it->second;

        std::string arg;
        while (ss >> arg)
        {
            // param comment
            if (arg[0] == '@')
                continue;

            // line comment
            if (arg[0] == '#')
                break;

            if (arg[0] == '\'')
            {
                print<uint16_t>(arg.size() - 2);
                std::cout << arg.substr(1, arg.size() - 2);
            }
            else if (std::isdigit(arg[0]) || arg[0] == '-')
            {
                auto type = arg[arg.size() - 1];
                auto src = arg.substr(0, arg.size() - 1);
                switch (type)
                {
                    case 'i':
                        encode<int32_t>(src);
                        break;
                    case 'u':
                        encode<uint32_t>(src);
                        break;
                    case 's':
                        encode<int16_t>(src);
                        break;
                    case 'h':
                        encode<uint16_t>(src);
                        break;
                    case 'c':
                        encode<char>(src);
                        break;
                    default:
                        encode<int32_t>(arg);
                        break;
                }
            }
            else
            {
                std::cerr << "invalid token '" << arg << "'" << std::endl;
                return 1;
            }
        }
    }

    if (!std::cin.eof())
    {
        std::cerr << "parse error" << std::endl;
        return 1;
    }
}
