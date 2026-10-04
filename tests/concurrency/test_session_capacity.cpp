#ifdef NDEBUG
#undef NDEBUG
#endif
#include "strata/core/session.hpp"
#include "strata/core/layer_range.hpp"
#include <cassert>
#include <cstdio>
int main() {
    using strata::core::weight_in_layer_range;
    assert(weight_in_layer_range("token_embd.weight",24,48));
    assert(weight_in_layer_range("blk.24.attn_q.weight",24,48));
    assert(weight_in_layer_range("blk.47.ssm_alpha.weight",24,48));
    assert(!weight_in_layer_range("blk.23.attn_q.weight",24,48));
    assert(!weight_in_layer_range("blk.48.attn_q.weight",24,48));
    assert(weight_in_layer_range("blk.unknown.weight",24,48));
    assert(weight_in_layer_range("blk.24x.weight",24,48));
    assert(weight_in_layer_range("blk.999999999999999999999.weight",24,48));
    assert(weight_in_layer_range("blk.23.attn_q.weight",24,-1));
    strata::core::ModelGeometry g;
    strata::core::qsa_set_kv_int8(false);
    strata::core::qsa_set_kv_q4(false);
    strata::core::qsa_set_kv_hybrid(false);
    const auto whole=strata::core::session_bytes(g,262144,10);
    const auto first=strata::core::session_bytes(g,262144,10,0,24);
    const auto last=strata::core::session_bytes(g,262144,10,24,48);
    assert(first==last && first<whole*7/10);
    // Six absent FP16 attention caches, each at least 512 MiB, must be removed.
    assert(whole-first>=6ull*512*1048576);
    assert(strata::core::session_bytes(g,262144,10,24,24)==0);
    assert(strata::core::session_bytes(g,262144,10,-1,24)==0);
    assert(strata::core::session_bytes(g,262144,10,0,49)==0);
    strata::core::qsa_set_kv_int8(true);
    assert(strata::core::session_bytes(g,262144,10,0,24)<first);
    std::printf("FP16 262K session: full=%llu MiB, 24-layer stage=%llu MiB\n",
                (unsigned long long)(whole>>20),(unsigned long long)(first>>20));
}
