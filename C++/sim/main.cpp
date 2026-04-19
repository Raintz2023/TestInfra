#include "Ate.h"
#include "Pattern.h"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

SocSchema dram_schema() {
    return SocSchema({
        {"R", true, 0, 1, DriveWaveform::nrz(), 0},
        {"W", true, 1, 1, DriveWaveform::nrz(), 0},
        {"ADDR", true, 2, 8, DriveWaveform::nrz(), 0},
        {"DQ_IN", true, 10, 8, DriveWaveform::nrz(), 0},
        {"MR_IN", true, 18, 8, DriveWaveform::nrz(), 0},
        {"MRW", true, 26, 1, DriveWaveform::nrz(), 0},
        {"MRR", true, 27, 1, DriveWaveform::nrz(), 0},
        {"DRIV", true, 28, 1, DriveWaveform::nrz(), 0},
        {"CLK", true, 29, 1, DriveWaveform::rzz(), 0},
        {"RST_N", true, 30, 1, DriveWaveform::nrz(), 1},
        {"DQ_IE", false, 0, 1, DriveWaveform::nrz(), 0},
        {"DQ_OUT", false, 1, 8, DriveWaveform::nrz(), 0},
        {"MR_OUT", false, 9, 8, DriveWaveform::nrz(), 0},
        {"DQ_OE", false, 17, 1, DriveWaveform::nrz(), 0},
        {"DQ_OUT_VALID", false, 18, 1, DriveWaveform::nrz(), 0},
    });
}

CommandSet dram_commands() {
    return CommandSet({
        {"MRWR", {{"MRW", false}, {"ADDR", true}, {"MR_IN", true}}},
        {"WR", {{"W", false}, {"ADDR", true}}},
        {"DRV", {{"DRIV", false}, {"DQ_IN", true}}},
        {"RD", {{"R", false}, {"ADDR", true}}},
        {"SMP", {{"DQ_OUT", true}}},
    });
}

std::string get_ti_root() {
    const char* ti = std::getenv("TI");
    if (ti == nullptr || ti[0] == '\0') {
        throw std::runtime_error("Environment variable TI is not set");
    }
    return std::string(ti);
}

}  // namespace

int main() {
    const std::string wave_name = get_ti_root() + "/C++/wave/dram.vcd";

    ATE ate(wave_name, true, 60);
    const auto schema = dram_schema();
    const auto commands = dram_commands();
    schema.configure(ate);

    apply_command(ate, schema, commands.command("MRWR"), {0, 8});
    apply_command(ate, schema, commands.command("MRWR"), {1, 8});
    apply_command(ate, schema, commands.command("WR"), {4});
    apply_command(ate, schema, commands.command("DRV"), {60});
    ate.run_cycles(8);
    apply_command(ate, schema, commands.command("RD"), {4});
    ate.run_cycles(10);
    expect_command(ate, schema, commands.command("SMP"), {60});
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
