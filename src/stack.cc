#include "stack.h"

Fin::Stack::Stack(std::size_t size)
{
    content = new char[size];
}

Fin::Stack::~Stack()
{
    delete content;
}
