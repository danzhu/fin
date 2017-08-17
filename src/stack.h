#ifndef FIN_STACK_H
#define FIN_STACK_H

#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include "log.h"
#include "type.h"
#include "typedefs.h"
#include "util.h"

namespace Fin
{
    class Stack
    {
        public:
            explicit Stack(Offset cap):
                _content{new char[cap.value]}, _cap{cap.value} {}

            Stack(const Stack &other) = delete;
            Stack(Stack &&other) = delete;

            ~Stack()
            {
                delete[] _content;
            }

            Stack &operator=(const Stack &other) = delete;
            Stack &operator=(Stack &&other) = delete;

            Offset size() const noexcept { return _size; }
            Offset capacity() const noexcept { return _cap; }
            void resize(Offset size) noexcept { _size = size; }
            char *content() const noexcept { return _content; }

            char *at(Offset off, Offset size)
            {
                if (off + size > _size)
                    throw std::out_of_range{"invalid stack access at "
                        + std::to_string(off.value)};

                return &_content[off.value];
            }

            char *pushSize(Offset size)
            {
                if (_size > _cap - size)
                    throw std::overflow_error{"stack overflow"};

                auto val = &_content[_size.value];

                LOG(2) << std::endl << "  < [" << _size << ", " << size << "]";

                _size += size;
                return val;
            }

            char *popSize(Offset size)
            {
                if (_size < size)
                    throw std::overflow_error{"negative stack size"};

                LOG(2) << std::endl << "  > [" << _size << ", " << size << "]";

                _size -= size;
                return &_content[_size.value];
            }

            char *topSize(Offset size)
            {
                if (_size < size)
                    throw std::overflow_error{"accessing at negative index"};

                LOG(2) << std::endl << "  ^ [" << _size << ", " << size << "]";

                return &_content[(_size - size).value];
            }

            template<typename T> T &at(Offset idx)
            {
                constexpr auto size = Offset{sizeof(T)}.align(MAX_ALIGN);

                return *reinterpret_cast<T*>(at(idx, size));
            }

            template<typename T> void push(T val)
            {
                constexpr auto size = Offset{sizeof(T)}.align(MAX_ALIGN);

                if (_size > _cap - size)
                    throw std::overflow_error{"stack overflow"};

                LOG(2) << std::endl << "  < " << val;
                LOG(2) << " [" << _size << ", " << size << "]";

                auto addr = _size;
                _size += size;
                at<T>(addr) = val;
            }

            template<typename T> void pop(T &val)
            {
                constexpr auto size = Offset{sizeof(T)}.align(MAX_ALIGN);

                if (_size < size)
                    throw std::overflow_error{"negative stack size"};

                val = at<T>(_size - size);

                LOG(2) << std::endl << "  > " << val;
                LOG(2) << " [" << _size << ", " << size << "]";

                _size -= size;
            }

            template<typename T> T pop()
            {
                T val;
                pop(val);
                return val;
            }

            template<typename T> T &top()
            {
                constexpr auto size = Offset{sizeof(T)}.align(MAX_ALIGN);

                if (_size < size)
                    throw std::runtime_error{"accessing at negative index"};

                auto &val = at<T>(_size - size);

                LOG(2) << std::endl << "  ^ " << val;
                LOG(2) << " [" << _size << ", " << size << "]";

                return val;
            }

        private:
            char *_content = nullptr;
            Offset _cap;
            Offset _size{0};
    };
}

#endif
