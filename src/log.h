#ifndef FIN_LOG_H
#define FIN_LOG_H

#include <iostream>
// TODO: change to varadic template function
#define LOG(lvl) FIN_DEBUG < lvl ? std::cerr : std::cerr

#endif
