#ifndef __RUNTIME_H__
#define __RUNTIME_H__

#include <iosfwd>
#include <map>
#include <memory>
#include <vector>
#include "method.h"
#include "module.h"
#include "stack.h"

namespace Fin
{
    class Runtime
    {
        Stack opStack;
        std::vector<std::unique_ptr<Module>> modules;
        std::map<ModuleID, Module *> modulesByID;
        std::vector<char> instrs;
        Module *currentModule;
        uint32_t pc;
        uint32_t fp;

        template<typename T> T readConst()
        {
            // TODO: change to cross-platform implementation
            auto val = *reinterpret_cast<T*>(&instrs.at(pc));
            pc += sizeof(T) / sizeof(char);
            return val;
        }
        template<typename T> void readConst(T &val)
        {
            val = readConst<T>();
        }

        template<typename T> void loadConst()
        {
            opStack.push(readConst<T>());
        }

        template<typename Op> void binaryOp()
        {
            auto op2 = opStack.pop<typename Op::second_argument_type>();
            auto op1 = opStack.pop<typename Op::first_argument_type>();
            opStack.push(Op{}(op1, op2));
        }

        int16_t frameOffset()
        {
            auto offset = readConst<int16_t>();
            if (offset < 0)
            {
                offset -= (sizeof(Module::id) + sizeof(Method::argSize)
                        + sizeof(pc) + sizeof(fp));
            }
            return offset;
        }

        template<typename T> void load()
        {
            opStack.push(opStack.at<T>(fp + frameOffset()));
        }

        template<typename T> void store()
        {
            opStack.pop(opStack.at<T>(fp + frameOffset()));
        }

        std::string readStr();
        void execute();
    public:
        void run(std::istream &src);
        Module &createModule(const ModuleID &id, uint16_t methodSize);
        uint32_t programCounter() const noexcept;
    };
}

#endif
