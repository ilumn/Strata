#pragma once
#include <cstdlib>
#include <cstdio>
#include <cstdint>
#include <fstream>
#include <stdexcept>
#include <vector>
struct UpstreamTrace {
    uint64_t serial_id = 0;
    std::ofstream output;
    UpstreamTrace() {
        const char* path=std::getenv("STRATA_UPSTREAM_TRACE");
        if(path) {
            output.open(path,std::ios::binary|std::ios::trunc);
            if(!output) throw std::runtime_error("trace open failed");
            std::fprintf(stderr,"UPSTREAM PARITY OVERLAY: forced single-token target path\n");
        }
    }
    bool enabled() const {return output.is_open();}
    template<class V> bool record(V& v,int row,uint64_t id,uint64_t step,uint64_t pos,int32_t& token,std::string& err) {
        if(!enabled())return true;
        std::vector<float> logits((size_t)v.vocab());
        if(!id || !v.copy_logits(row,logits.data())) {err="trace copy failed";return false;}
        uint64_t h[]={id,step,pos,logits.size()};
        output.write((const char*)h,sizeof(h));output.write((const char*)logits.data(),logits.size()*sizeof(float));output.flush();
        if(!output){err="trace write failed";return false;}
        constexpr int32_t sequence[]={198,40,1077,220,19,13,198,791,4226,374,220,19,13,198,40,1077};
        token=sequence[step%16];return true;
    }
};
