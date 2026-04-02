#include "Ate.h"

#include <cstdint>
#include <iostream>
#include <string>

namespace {

void mrw(ATE& ate, uint16_t addr, uint16_t input, int delay) {
    
    ate.stage_drive_pin(26, 1, delay);
    ate.stage_drive_field(2, 8, addr, delay);
    ate.stage_drive_field(18, 8, input, delay);
    ate.pulse_drive();
    
}

int mrr(ATE& ate, uint16_t addr, int delay) {
    
    ate.stage_drive_pin(27, 1, delay);
    ate.stage_drive_field(2, 8, addr, delay);
    ate.pulse_drive();
    
    return 0;
}

}  // namespace

int main() {
    const std::string wave_name =
        "/home/seagull/Code/TestInfra/C++/wave/dram.vcd";

    ATE ate(wave_name, true, 60);
    std::cout << ate.get_top_data() << std::endl;

    for (int y = 0; y < 100; y++) {
        mrw(ate, 0, 60, 10);
        mrr(ate, 0, 10);
        for (int x =0; x < y; x++) {
            ate.tick();
        }
        ate.compare(CompareSpec::field(9, 8, 0));
        ate.print_compare_results();
        ate.clear_compare_results();
        ate.reset();
    }

}
