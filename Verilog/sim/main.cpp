#include "Ate.h"

#include <cstdint>
#include <iostream>
#include <string>

namespace {

void mrw(ATE& ate, uint16_t addr, uint16_t input) {
    
    ate.stage_drive_pin(26, 1, 0);
    ate.stage_drive_field(2, 8, addr, 0);
    ate.stage_drive_field(18, 8, input, 0);
    ate.pulse_drive();
    
}

int mrr(ATE& ate, uint16_t addr) {
    
    ate.stage_drive_pin(27, 1, 0);
    ate.stage_drive_field(2, 8, addr, 0);
    ate.pulse_drive();
    
    return 0;
}

bool mr_cp(ATE& ate, uint16_t addr, uint16_t input) {
    const uint8_t expected = input;

    mrw(ate, addr, input);

    ate.tick();

    mrr(ate, addr);

    ate.stage_sample_field(9, 8, 0);
    // ate.stage_sample_all();
    ate.pulse_sample();

    const bool pass = ate.compare();
    if (!pass) {
        std::cout << "  input=0x" << std::hex << input
                  << " expected=0x" << static_cast<unsigned>(expected)
                  << " got=0x" << ate.last_sampled_raw()
                  << std::dec << '\n';
    }
    ate.tick();
    ate.tick();
    ate.tick();
    ate.tick();

    return pass;
};

}  // namespace

int main() {
    const std::string wave_name =
        "/home/seagull/Code/TestInfra/Verilog/wave/dram.vcd";

    ATE ate(wave_name, true, 50);
    std::cout << ate.get_top_data() << std::endl;
    if (mr_cp(ate, 0, 50)) {
        ate.print("pass");
    }
    else {
        ate.print("fail");
    }

}
