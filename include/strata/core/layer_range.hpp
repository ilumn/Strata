#pragma once
#include <string_view>
#include <cstdint>
namespace strata::core {
// Shared model tensors remain present on every stage; blk.N tensors belong only
// to the stage that executes layer N. Unknown names are retained conservatively.
inline bool weight_in_layer_range(std::string_view name, int64_t begin, int64_t end) {
    if (end < 0 || !name.starts_with("blk.")) return true;
    size_t i=4; int64_t layer=0; bool digit=false;
    while (i<name.size() && name[i]>='0' && name[i]<='9') {
        digit=true;
        if (layer>1000000) return true;
        layer=layer*10+name[i++]-'0';
    }
    if (!digit || i>=name.size() || name[i]!='.') return true;
    return layer>=begin && layer<end;
}
}
