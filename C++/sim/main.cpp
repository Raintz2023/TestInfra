#include "Ate.h"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

std::string get_ti_root() {
    const char* ti = std::getenv("TI");
    if (ti == nullptr || ti[0] == '\0') {
        throw std::runtime_error("Environment variable TI is not set");
    }
    return std::string(ti);
}

void configure_dram_socket(ATE& ate) {
    ate.clear_input_pin_configs();
    ate.clear_output_pin_configs();

    ate.configure_input_pin(0, 1, DriveWaveform::nrz(), 0);    // R
    ate.configure_input_pin(1, 1, DriveWaveform::nrz(), 0);    // W
    ate.configure_input_pin(2, 8, DriveWaveform::nrz(), 0);    // ADDR
    ate.configure_input_pin(10, 8, DriveWaveform::nrz(), 0);   // DQ_IN
    ate.configure_input_pin(18, 8, DriveWaveform::nrz(), 0);   // MR_IN
    ate.configure_input_pin(26, 1, DriveWaveform::nrz(), 0);   // MRW
    ate.configure_input_pin(27, 1, DriveWaveform::nrz(), 0);   // MRR
    ate.configure_input_pin(28, 1, DriveWaveform::nrz(), 0);   // DRIV
    ate.configure_input_pin(29, 1, DriveWaveform::rzz(), 0);   // CLK
    ate.configure_input_pin(30, 1, DriveWaveform::nrz(), 1);   // RST_N

    ate.configure_output_pin(0, 1, 0);   // DQ_IE
    ate.configure_output_pin(1, 8, 0);   // DQ_OUT
    ate.configure_output_pin(9, 8, 0);   // MR_OUT
    ate.configure_output_pin(17, 1, 0);  // DQ_OE
    ate.configure_output_pin(18, 1, 0);  // DQ_OUT_VALID
}

void mrwr(ATE& ate, uint32_t addr, uint32_t value) {
    ate.begin_vector_row();
    ate.activate_input_pin(26);
    ate.set_input_field(2, 8, addr);
    ate.set_input_field(18, 8, value);
    ate.commit_vector_row();
}

void wr(ATE& ate, uint32_t addr) {
    ate.begin_vector_row();
    ate.activate_input_pin(1);
    ate.set_input_field(2, 8, addr);
    ate.commit_vector_row();
}

void drv(ATE& ate, uint32_t value) {
    ate.begin_vector_row();
    ate.activate_input_pin(28);
    ate.set_input_field(10, 8, value);
    ate.commit_vector_row();
}

void rd(ATE& ate, uint32_t addr) {
    ate.begin_vector_row();
    ate.activate_input_pin(0);
    ate.set_input_field(2, 8, addr);
    ate.commit_vector_row();
}

}  // namespace

int main() {
    const std::string wave_name = get_ti_root() + "/C++/wave/dram.vcd";

    ATE ate(wave_name, true, 60);
    configure_dram_socket(ate);

    mrwr(ate, 0, 8);
    mrwr(ate, 1, 8);
    wr(ate, 4);
    drv(ate, 60);
    ate.run_cycles(8);
    rd(ate, 4);
    ate.run_cycles(10);
    ate.begin_vector_row();
    ate.expect_output_field(1, 8, 60);
    const bool pass = ate.compare_last();

    std::cout << "MRW=" << ate.drive_count(26)
              << " W=" << ate.drive_count(1)
              << " R=" << ate.drive_count(0)
              << " DRIV=" << ate.drive_count(28)
              << " CLK=" << ate.drive_count(29)
              << " RST_N=" << ate.drive_count(30)
              << " PASS=" << pass
              << std::endl;
}
