#include "Ate.h"

#include <cstdint>
#include <iostream>
#include <string>

namespace {

uint8_t expected_encoder_output(uint16_t input) {
    uint8_t encoded = 0;
    for (int bit = 0; bit < 16; ++bit) {
        if (((input >> bit) & 1U) != 0U) {
            encoded = static_cast<uint8_t>(bit);
        }
    }
    return encoded;
}

bool run_case(ATE& ate, uint16_t input) {
    const uint8_t expected = expected_encoder_output(input);

    ate.set_top_data(expected);

    // Drive Encoder input pins [15:0].
    ate.stage_drive_field(0, 16, input, 0);
    ate.pulse_drive();

    // Sample immediately after the drive pulse.
    // For the current PinInDriver + Encoder timing, the valid encoded output
    // is present right after pulse_drive() completes.
    ate.stage_sample_all(0);
    ate.pulse_sample();

    const bool pass = ate.compare();
    if (!pass) {
        std::cout << "  input=0x" << std::hex << input
                  << " expected=0x" << static_cast<unsigned>(expected)
                  << " got=0x" << ate.last_sampled_raw()
                  << std::dec << '\n';
    }
    return pass;
}

}  // namespace

int main() {
    const std::string wave_name =
        "/home/seagull/Code/TestInfra/Verilog/wave/encoder_smoke.vcd";

    ATE ate(wave_name, true, 0);

    int pass_count = 0;
    int total_count = 0;

    for (int bit = 0; bit < 16; ++bit) {
        total_count += 1;
        if (run_case(ate, static_cast<uint16_t>(1U << bit))) {
            pass_count += 1;
        }
    }

    total_count += 1;
    if (run_case(ate, static_cast<uint16_t>(0x0000))) {
        pass_count += 1;
    }

    total_count += 1;
    if (run_case(ate, static_cast<uint16_t>(0x8001))) {
        pass_count += 1;
    }

    std::cout << '\n'
              << "Encoder summary: " << pass_count << "/" << total_count
              << " passed" << std::endl;

    return pass_count == total_count ? 0 : 1;
}
