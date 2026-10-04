#ifdef NDEBUG
#undef NDEBUG
#endif
#include "strata/program/image_request.hpp"
#include <cassert>
#include <filesystem>
#include <limits>
#include <chrono>
using namespace strata::program;
int main() {
    const auto path = std::filesystem::temp_directory_path()/
        ("strata-image-test-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count())+".sve");
    struct Cleanup { std::filesystem::path p; ~Cleanup() { std::filesystem::remove(p); } } cleanup{path};
    auto write = [&](int count, int nx, int ny, int width, int values, bool nan = false) {
        std::ofstream f(path,std::ios::binary);
        int32_t h[5]={0x31455653,count,nx,ny,width}; f.write((char*)h,sizeof(h));
        for (int i=0;i<values;++i) { float x=nan?std::numeric_limits<float>::quiet_NaN():(float)i; f.write((char*)&x,4); }
    };
    constexpr int64_t image=248056;
    const std::vector<int64_t> tokens{10,image,image,image,image,11,12};
    ImagePrompt result; std::string err;
    write(4,2,2,4,16);
    assert(load_image_prompt(path.string(),tokens,4,32,result,err));
    assert(result.row_offsets==std::vector<int64_t>({-1,0,4,8,12,-1,-1}));
    assert(result.positions[3]==1 && result.positions[4]==1 && result.positions[5]==1);
    assert(result.positions[6]==1 && result.positions[7]==1 && result.positions[8]==2);
    assert(result.positions[9]==1 && result.positions[10]==2 && result.positions[11]==1);
    assert(result.positions[15]==3 && result.positions[18]==4); // text follows compressed image positions
    assert(result.positions[21]==5 && result.positions.size()==(32+64)*3);
    // Invalid inputs must be rejected without changing the last valid request.
    const auto saved=result.values;
    for (auto bad: {std::vector<int64_t>{10,image,11}, std::vector<int64_t>{10,image,image,image,image},
                   std::vector<int64_t>{10,image,image,11,image,image,12}, std::vector<int64_t>{10,11}}) {
        assert(!load_image_prompt(path.string(),bad,4,32,result,err)); assert(result.values==saved);
    }
    write(4,2,2,5,20); assert(!load_image_prompt(path.string(),tokens,4,32,result,err));
    write(4,3,2,4,16); assert(!load_image_prompt(path.string(),tokens,4,32,result,err));
    write(4,2,2,4,15); assert(!load_image_prompt(path.string(),tokens,4,32,result,err));
    write(4,2,2,4,16,true); assert(!load_image_prompt(path.string(),tokens,4,32,result,err));
    assert(result.values==saved);
}
