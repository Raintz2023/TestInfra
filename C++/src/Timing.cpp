#include "Timing.h"

#include <stdexcept>

void validate_timing_set(const TimingSet& timing) {
    if (timing.prd == 0) {
        throw std::invalid_argument("timing prd must be positive");
    }
    if (timing.nrz.edge >= timing.prd) {
        throw std::out_of_range("timing nrz.edge out of period range");
    }
    if (timing.stb.edge >= timing.prd) {
        throw std::out_of_range("timing stb.edge out of period range");
    }
    if (timing.rz.edge_1 >= timing.prd) {
        throw std::out_of_range("timing rz.edge_1 out of period range");
    }
    if (timing.rz.edge_2 >= timing.prd) {
        throw std::out_of_range("timing rz.edge_2 out of period range");
    }
    if (timing.rzz.edge_1 >= timing.prd) {
        throw std::out_of_range("timing rzz.edge_1 out of period range");
    }
    if (timing.rzz.edge_2 >= timing.prd) {
        throw std::out_of_range("timing rzz.edge_2 out of period range");
    }
    if (timing.rz.edge_1 >= timing.rz.edge_2) {
        throw std::invalid_argument("timing rz.edge_1 must be before rz.edge_2");
    }
    if (timing.rzz.edge_1 >= timing.rzz.edge_2) {
        throw std::invalid_argument("timing rzz.edge_1 must be before rzz.edge_2");
    }
}
