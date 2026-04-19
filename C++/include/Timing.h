#pragma once

#include <cstdint>
#include <string>

struct TimingSet {
    std::string name = "TS0";
    uint32_t period_phases = 10;
    uint32_t nrz_rise_phase = 1;
    uint32_t rzz_rise_phase = 2;
    uint32_t rzz_fall_phase = 7; // 7 - 2 = 5 half of period
    uint32_t sample_phase = 8;
};

void validate_timing_set(const TimingSet& timing);
