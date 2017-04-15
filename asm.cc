#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>

std::map<std::string, char> readOpcodes(const std::string &filename)
{
    std::map<std::string, char> opcodes;
    std::ifstream src{filename};

    std::string line;
    char opcode = 0;

    while (std::getline(src, line))
        opcodes.emplace(line.substr(0, line.size() - 1), opcode++);

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
    auto opcodes = readOpcodes("src/opcodes");

    std::string op;
    while (std::cin >> op)
    {
        if (op[0] == '@')
            continue;

        if (op[0] == '\'')
        {
            print<uint16_t>(op.size() - 2);
            std::cout << op.substr(1, op.size() - 2);
        }
        else if (std::isdigit(op[0]) || op[0] == '-')
        {
            auto type = op[op.size() - 1];
            auto src = op.substr(0, op.size() - 1);
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
                    encode<int32_t>(op);
                    break;
            }
        }
        else if (opcodes.find(op) != opcodes.end())
        {
            std::cout << opcodes.at(op);
        }
        else
        {
            std::cerr << "invalid token" << std::endl;
            return 1;
        }
    }

    if (!std::cin.eof())
    {
        std::cerr << "parse error" << std::endl;
        return 1;
    }
}
