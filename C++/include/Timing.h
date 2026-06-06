#pragma once

#include <cstdint>
#include <string>

struct TimingSet {
    std::string name = "TS0";
    uint32_t period_phases = 10;
    uint32_t nrz_rise_phase = 1;
    int32_t nrz_base_phase = 0;
    uint32_t rz_rise_phase = 1;
    uint32_t rz_return_phase = 3;
    int32_t rz_base_phase = 0;
    uint32_t rzz_rise_phase = 2;
    uint32_t rzz_fall_phase = 7; // 7 - 2 = 5 half of period
    int32_t rzz_base_phase = 0;
    uint32_t sample_phase = 8;
    int32_t sample_base_phase = 0;
};

void validate_timing_set(const TimingSet& timing);
