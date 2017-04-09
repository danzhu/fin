#ifndef __RUNTIME_H__
#define __RUNTIME_H__

#include <iosfwd>
#include <vector>
#include "method.h"
#include "stack.h"

namespace Fin
{
    class Runtime
    {
        Stack opStack;
        std::vector<Method> methods;
        std::vector<char> instrs;
        uint32_t pc;
        uint32_t fp;

        template<typename T> T readConst() noexcept
        {
            // TODO: change to cross-platform implementation
            auto val = *reinterpret_cast<T*>(&instrs.at(pc));
            pc += sizeof(T) / sizeof(char);
            return val;
        }

        template<typename T> void loadConst() noexcept
        {
            opStack.push(readConst<T>());
        }

        template<typename Op> void binaryOp() noexcept
        {
            auto op2 = opStack.pop<typename Op::second_argument_type>();
            auto op1 = opStack.pop<typename Op::first_argument_type>();
            opStack.push(Op{}(op1, op2));
        }

        template<typename T> void load() noexcept
        {
            auto offset = readConst<int16_t>();
            opStack.push(opStack.at<T>(fp + offset));
        }

        template<typename T> void store() noexcept
        {
            auto offset = readConst<int16_t>();
            opStack.at<T>(fp + offset) = opStack.pop<T>();
        }

        void execute();
    public:
        void run(std::istream &src);
    };
}

#endif
