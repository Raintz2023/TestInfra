#include "AteBench.h"

#include <cstdint>
#include <iostream>
#include <string>
#include <utility>

namespace {

AteEvent make_write_frame(uint8_t value) {
    AteEvent event{"write_frame"};
    event
        .idle(1)
        .run(VectorRow{}.drive("DQS_RX_BIT", 0))
        .run(VectorRow{}.drive("DQS_RX_BIT", 0))
        .run(VectorRow{}.drive("DQS_RX_BIT", 1))
        .run(VectorRow{}.drive("DQS_RX_BIT", 1));

    for (int bit = 0; bit < 8; ++bit) {
        const uint32_t dqs = static_cast<uint32_t>(bit & 1);
        const uint32_t dq = static_cast<uint32_t>((value >> bit) & 1U);
        event.run(VectorRow{}.drive("DQS_RX_BIT", dqs).drive("DQ_RX_BIT", dq));
    }

    event
        .run(VectorRow{}.drive("DQS_RX_BIT", 0))
        .run(VectorRow{}.drive("DQS_RX_BIT", 0));
    return event;
}

AteEvent make_read_frame(uint8_t expected) {
    AteEvent event{"read_expect_frame"};
    event
        .idle(1)
        .run(VectorRow{}.sample("DQS_TX_BIT", 0))
        .run(VectorRow{}.sample("DQS_TX_BIT", 0))
        .run(VectorRow{}.sample("DQS_TX_BIT", 1))
        .run(VectorRow{}.sample("DQS_TX_BIT", 1));

    for (int bit = 0; bit < 8; ++bit) {
        const uint32_t dqs = static_cast<uint32_t>(bit & 1);
        const uint32_t dq = static_cast<uint32_t>((expected >> bit) & 1U);
        event.run(VectorRow{}.sample("DQS_TX_BIT", dqs).sample("DQ_TX_BIT", dq));
    }

    event
        .run(VectorRow{}.sample("DQS_TX_BIT", 0))
        .run(VectorRow{}.sample("DQS_TX_BIT", 0));
    return event;
}

}  // namespace

int main(int argc, char** argv) {
    const std::string wave_path = argc > 1
        ? argv[1]
        : "C++/wave/wave_voltage.vcd";

    // ATE-side drive voltage for DQ/DQS. The ATE is ideal: it switches between
    // VIL and VIH immediately. Dram owns the pad slew and Vref comparison.
    AteInputVoltageConfig ate_input_voltage;
    ate_input_voltage.vil_uv = 0;
    ate_input_voltage.vih_uv = 1'200'000;

    DutInputInterfaceConfig dut_input_interface;
    dut_input_interface.enabled = true;
    // Compatibility field for the generic DUT interface bus. Chip/Dram now
    // derives DQ/DQS Vref internally from POWER VDDQ and MR5.
    dut_input_interface.vref_uv = 600'000;
    dut_input_interface.rise_step_uv = 100'000;
    dut_input_interface.fall_step_uv = 100'000;

    // Output demonstration on DQ_TX_BIT and DQS_TX_BIT. Their DUT-side bits
    // become finite-slew voltages; VOL/VOH mark valid 0/1 and the middle band
    // drives SAMP_VALID low.
    // AteOutputVoltageConfig ate_output_voltage;
    // ate_output_voltage.enabled = true;
    // ate_output_voltage.vol_uv = 300'000;
    // ate_output_voltage.voh_uv = 900'000;

    DutOutputInterfaceConfig dut_output_interface;
    dut_output_interface.enabled = true;
    dut_output_interface.low_uv = 200'000;
    dut_output_interface.high_uv = 1'000'000;
    dut_output_interface.rise_step_uv = 50'000;
    dut_output_interface.fall_step_uv = 50'000;

    AteBenchConfig config{
        .wave_path = wave_path,
        .trace_enable = true,
        .inputs = {
            {"CLK",        0, 1, DriveWaveform::rzz(), 0},
            {"RST_N",      1, 1, DriveWaveform::rz(true), 1},
            {"R",          2, 1, DriveWaveform::rz(), 0},
            {"W",          3, 1, DriveWaveform::rz(), 0},
            {"ADDR",       4, 8, DriveWaveform::nrz(), 0},
            {"DQ_RX_BIT", 12, 1, DriveWaveform::nrz(true), 1, ate_input_voltage},
            {"DQS_RX_BIT",13, 1, DriveWaveform::nrz(true), 1, ate_input_voltage},
            {"MR_IN",     14, 8, DriveWaveform::nrz(), 0},
            {"MRW",       22, 1, DriveWaveform::rz(), 0},
            {"MRR",       23, 1, DriveWaveform::rz(), 0},
        },
        // .outputs = {
        //     {"DQ_IE",        0, 1, std::nullopt},
        //     {"DQ_TX_BIT",    1, 1, ate_output_voltage},
        //     {"DQS_TX_BIT",   2, 1, ate_output_voltage},
        //     {"DQ_OE",        3, 1, std::nullopt},
        //     {"DQ_OUT_VALID", 4, 1, std::nullopt},
        // },
        .dut_interface = {
            .inputs = {
                {"DQ_RX_BIT", dut_input_interface},
                {"DQS_RX_BIT", dut_input_interface},
            },
            .outputs = {
                {"DQ_TX_BIT", dut_output_interface},
                {"DQS_TX_BIT", dut_output_interface},
            },
        },
        .power_uv = {
            {"VDDQ", 1'200'000},
        },
        .skew = {
            .rx_dqs = 0,
            .rx_dq = 0,
            .tx_dqs = 0,
            .tx_dq = 0,
        },
    };

    int xlp;
    int ylp;
    for (ylp = 0; ylp <= 1200; ylp += 100) {
        AteOutputVoltageConfig ate_output_voltage;
        ate_output_voltage.enabled = true;
        ate_output_voltage.vol_uv = static_cast<uint32_t>(ylp) * 1000U;
        ate_output_voltage.voh_uv = static_cast<uint32_t>(ylp) * 1000U;

        for (xlp = -79 ; xlp <= 100; xlp += 2) {
            TimingSet timing;
            timing.name = "TS_VOLTAGE_DEMO";
            timing.prd = 100;
            timing.nrz = {10, 0};
            timing.rz = {10, 30, 0};
            timing.rzz = {20, 70, 0};
            timing.stb = {80, xlp};

            config.timing = timing;
            config.outputs = {
                {"DQ_IE",        0, 1, std::nullopt},
                {"DQ_TX_BIT",    1, 1, ate_output_voltage},
                {"DQS_TX_BIT",   2, 1, ate_output_voltage},
                {"DQ_OE",        3, 1, std::nullopt},
                {"DQ_OUT_VALID", 4, 1, std::nullopt},
            };

            AteBench bench(config);

            bench.run(VectorRow{}.pulse("RST_N").alert());
            bench.idle(1);

            bench.run(VectorRow{}.pulse("MRW").drive("ADDR", 0).drive("MR_IN", 35));
            bench.idle(1);

            bench.run(VectorRow{}.pulse("MRW").drive("ADDR", 1).drive("MR_IN", 35));
            bench.idle(1);

            bench.run(VectorRow{}.pulse("MRW").drive("ADDR", 5).drive("MR_IN", 100));
            bench.idle(1);

            bench.run(VectorRow{}.pulse("W").drive("ADDR", 0));

            bench.wait_rising("DQ_IE", 100, make_write_frame(0xA5));

            bench.idle(2);

            bench.run(VectorRow{}.pulse("R").drive("ADDR", 0));

            bench.wait_rising("DQ_OE", 100, make_read_frame(0xA5));

            bench.idle(2);

            if (bench.compare_all()) {
                std::printf("*");
            }
            else {
                std::printf(".");
            }

        }
        std::printf("\n");

    }
    return 0;
}
