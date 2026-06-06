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

    ate.configure_input_pin(0, 1, DriveWaveform::rzz(), 0);  // CLK
    ate.configure_input_pin(1, 1, DriveWaveform::nrz(), 1);  // RST_N
    ate.configure_input_pin(2, 1, DriveWaveform::rz(), 0);   // DQ_RX_START
    ate.configure_input_pin(3, 1, DriveWaveform::rz(), 0);   // R
    ate.configure_input_pin(4, 1, DriveWaveform::rz(), 0);   // W
    ate.configure_input_pin(5, 8, DriveWaveform::nrz(), 0);  // ADDR
    ate.configure_input_pin(13, 1, DriveWaveform::nrz(), 0); // DQ_RX_BIT
    ate.configure_input_pin(14, 8, DriveWaveform::nrz(), 0); // MR_IN
    ate.configure_input_pin(22, 1, DriveWaveform::rz(), 0);  // MRW
    ate.configure_input_pin(23, 1, DriveWaveform::rz(), 0);  // MRR

    ate.configure_output_pin(0, 1, 0);  // DQ_IE
    ate.configure_output_pin(1, 1, 0);  // DQ_TX_BIT
    ate.configure_output_pin(2, 1, 0);  // DQ_OE
    ate.configure_output_pin(3, 1, 0);  // DQ_OUT_VALID
}

void mrwr(ATE& ate, uint32_t addr, uint32_t value) {
    ate.begin_vector_row();
    ate.activate_input_pin(22);
    ate.set_input_field(5, 8, addr);
    ate.set_input_field(14, 8, value);
    ate.commit_vector_row();
}

void wr(ATE& ate, uint32_t addr) {
    ate.begin_vector_row();
    ate.activate_input_pin(4);
    ate.set_input_field(5, 8, addr);
    ate.commit_vector_row();
}

void serial_bit(ATE& ate, bool start, uint32_t value) {
    ate.begin_vector_row();
    if (start) {
        ate.activate_input_pin(2);
    }
    ate.set_input_field(13, 1, value);
    ate.commit_vector_row();
}

void serial_byte(ATE& ate, uint32_t value) {
    serial_bit(ate, true, 0);
    for (int i = 7; i >= 0; --i) {
        serial_bit(ate, false, (value >> i) & 1U);
    }
    serial_bit(ate, false, 1);
}

void rd(ATE& ate, uint32_t addr) {
    ate.begin_vector_row();
    ate.activate_input_pin(3);
    ate.set_input_field(5, 8, addr);
    ate.commit_vector_row();
}

}  // namespace

int main() {
    const std::string wave_name = get_ti_root() + "/C++/wave/dram.vcd";

    ATE ate(wave_name, false, 60);
    configure_dram_socket(ate);

    mrwr(ate, 0, 8);
    mrwr(ate, 1, 8);
    wr(ate, 4);
    serial_byte(ate, 60);
    ate.run_cycles(8);
    rd(ate, 4);
    ate.run_cycles(10);

    std::cout << "MRW=" << ate.drive_count(22)
              << " W=" << ate.drive_count(4)
              << " R=" << ate.drive_count(3)
              << " DQ_RX_START=" << ate.drive_count(2)
              << " CLK=" << ate.drive_count(0)
              << " RST_N=" << ate.drive_count(1)
              << std::endl;
}
