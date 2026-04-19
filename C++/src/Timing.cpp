#include "Timing.h"

#include <stdexcept>

void validate_timing_set(const TimingSet& timing) {
    if (timing.period_phases == 0) {
        throw std::invalid_argument("timing period_phases must be positive");
    }
    if (timing.nrz_rise_phase >= timing.period_phases) {
        throw std::out_of_range("timing nrz_rise_phase out of period range");
    }
    if (timing.sample_phase >= timing.period_phases) {
        throw std::out_of_range("timing sample_phase out of period range");
    }
    if (timing.rzz_rise_phase >= timing.period_phases) {
        throw std::out_of_range("timing rzz_rise_phase out of period range");
    }
    if (timing.rzz_fall_phase >= timing.period_phases) {
        throw std::out_of_range("timing rzz_fall_phase out of period range");
    }
    if (timing.nrz_rise_phase >= timing.rzz_rise_phase) {
        throw std::invalid_argument("timing nrz_rise_phase must be before rzz_rise_phase");
    }
    if (timing.rzz_rise_phase >= timing.rzz_fall_phase) {
        throw std::invalid_argument("timing rzz_rise_phase must be before rzz_fall_phase");
    }
}
