#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <string>
#include <vector>

namespace strata::program {
struct ImagePrompt {
    std::vector<float> values;
    std::vector<int64_t> row_offsets; // -1 for text; float offset for an image row
    std::vector<int32_t> positions;  // [cell][time,height,width], including continuation
};
inline bool load_image_prompt(const std::string& path, const std::vector<int64_t>& tokens,
                              int64_t width, int64_t context, ImagePrompt& result, std::string& err) {
    constexpr int64_t image_pad = 248056;
    if (width < 1 || context < 1 || tokens.empty() || tokens.size() > (size_t)context) {
        err = "image request: invalid dimensions/context"; return false;
    }
    std::ifstream file(path, std::ios::binary);
    if (!file) { err = "image request: cannot open embeddings"; return false; }
    struct Image { int64_t n, nx, ny; size_t offset; };
    std::vector<Image> images;
    ImagePrompt built;
    size_t total_rows = 0;
    while (true) {
        int32_t h[5]{};
        file.read((char*)h, sizeof(h));
        if (file.gcount() == 0 && file.eof()) break;
        if (file.gcount() != sizeof(h) || h[0] != 0x31455653 || h[1] < 1 || h[2] < 1 || h[3] < 1 ||
            (int64_t)h[2] * h[3] != h[1] || h[4] != width || (size_t)h[1] > tokens.size() - total_rows) {
            err = "image request: invalid embedding record"; return false;
        }
        const size_t offset = built.values.size(), count = (size_t)h[1] * (size_t)width;
        built.values.resize(offset + count);
        file.read((char*)(built.values.data() + offset), (std::streamsize)(count * sizeof(float)));
        if (file.gcount() != (std::streamsize)(count * sizeof(float)) ||
            !std::all_of(built.values.begin() + offset, built.values.end(), [](float v) { return std::isfinite(v); })) {
            err = "image request: short or non-finite embedding record"; return false;
        }
        images.push_back({h[1], h[2], h[3], offset}); total_rows += (size_t)h[1];
    }
    if (images.empty() || tokens.back() == image_pad) {
        err = "image request: no images, or prompt ends in an image"; return false;
    }
    built.row_offsets.assign(tokens.size(), -1);
    built.positions.resize((size_t)(context + 64) * 3);
    auto put = [&](int64_t i, int64_t t, int64_t h, int64_t w) {
        built.positions[(size_t)i*3] = (int32_t)t;
        built.positions[(size_t)i*3+1] = (int32_t)h;
        built.positions[(size_t)i*3+2] = (int32_t)w;
    };
    int64_t i = 0, p = 0; size_t k = 0;
    while (i < (int64_t)tokens.size()) {
        if (tokens[(size_t)i] != image_pad) { put(i++,p,p,p); ++p; continue; }
        if (k == images.size()) { err = "image request: prompt has more images than embeddings"; return false; }
        const auto& im = images[k++];
        if (im.n > (int64_t)tokens.size()-i) { err = "image request: insufficient image tokens"; return false; }
        for (int64_t j = 0; j < im.n; ++j) {
            if (tokens[(size_t)(i+j)] != image_pad) { err = "image request: interrupted image token span"; return false; }
            put(i+j,p,p+j/im.nx,p+j%im.nx);
            built.row_offsets[(size_t)(i+j)] = (int64_t)im.offset+j*width;
        }
        i += im.n; p += std::max(im.nx,im.ny);
    }
    if (k != images.size()) { err = "image request: embeddings have more images than prompt"; return false; }
    for (; i < context+64; ++i,++p) put(i,p,p,p);
    result = std::move(built);
    return true;
}
}
