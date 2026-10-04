#pragma once
#include "strata/kernels/mrope.hpp"

namespace strata::core {
// CUDA graphs capture this pointer. Scope every member's recording separately so
// a batch can contain pictures with different position grids on the same GPU.
class MropeScope {
public:
    explicit MropeScope(const int32_t* table) : previous_(kernels::mrope_table()) {
        kernels::mrope_table_set(table);
    }
    ~MropeScope() { kernels::mrope_table_set(previous_); }
    MropeScope(const MropeScope&) = delete;
    MropeScope& operator=(const MropeScope&) = delete;
private:
    const int32_t* previous_;
};
}
