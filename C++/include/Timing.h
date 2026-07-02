#pragma once

#include <cstdint>
#include <string>

struct SingleEdgeTiming {
    uint32_t edge = 1;
    int32_t base = 0;
};

struct TwoEdgeTiming {
    uint32_t edge_1 = 1;
    uint32_t edge_2 = 3;
    int32_t base = 0;
};

struct TimingSet {
    std::string name = "TS0";
    uint32_t prd = 10;
    SingleEdgeTiming nrz{1, 0};
    TwoEdgeTiming rz{1, 3, 0};
    TwoEdgeTiming rzz{2, 7, 0};
    SingleEdgeTiming stb{8, 0};
};

void validate_timing_set(const TimingSet& timing);
