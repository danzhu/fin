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
        Module *execModule;
        uint32_t pc;
        uint32_t fp;

        std::string readStr();
        void jump(int16_t target);
        int16_t frameOffset();
        void ret();
        void execute();
        void call(const Method &method);

        template<typename T> T readConst()
        {
            std::make_unsigned_t<T> val{};
            for (uint16_t i = 0; i < sizeof(T); ++i)
                val |= instrs.at(pc + i) << (i * 8);
            jump(pc + sizeof(T));
            return *reinterpret_cast<T*>(&val);
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

        template<typename T> void load()
        {
            opStack.push(opStack.at<T>(fp + frameOffset()));
        }

        template<typename T> void store()
        {
            opStack.pop(opStack.at<T>(fp + frameOffset()));
        }

        template<typename T> void ret()
        {
            auto val = opStack.pop<T>();
            ret();
            opStack.push(val);
        }
    public:
        void run(std::istream &src);
        Module &createModule(const std::string &name);
        Module &getModule(const std::string &name);
        uint32_t programCounter() const noexcept;
    };
}

#endif
