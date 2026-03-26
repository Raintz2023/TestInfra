#pragma once

#include "VSocket.h"
#include "verilated.h"
#include "verilated_vcd_c.h"

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#ifdef ATE_PYBIND
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#endif

struct SampleRecord {
    // Sample actually returned by the DUT at this cycle.
    uint64_t cycle = 0;
    // Which output pins actually asserted SAMP_ALERT on this cycle.
    uint32_t sample_mask = 0;
    // Raw packed SAMP_OUT value from the socket.
    uint32_t raw = 0;
};

class ATE {
public:
    // Basic socket geometry exposed to wrappers so customer-level protocols
    // can build on top of the generic ATE primitives.
    static constexpr int kOffsetWidth = 4;
    static constexpr int kMaxOffset = (1 << kOffsetWidth) - 1;
    static constexpr int kPinInCount = 29;
    static constexpr int kPinOutCount = 19;

    explicit ATE(std::string wave_name = {},
                 bool trace_enable = true,
                 uint8_t top_data_init = 0);

    ~ATE();

    // Common external APIs: basic simulation lifecycle.
    void tick();
    void run_cycles(uint32_t cycles);
    void reset();

    // Common external APIs: clear currently staged drive/sample commands
    // before building the next custom operation.
    void clear_drive();
    void clear_sample();

    // Common external APIs: generic drive primitives.
    // These are the main methods you will usually wrap into customer-specific
    // commands such as write/read/strobe/command packets.
    void stage_drive_pin(int pin, bool value, uint32_t delay = 0);
    void stage_drive_field(int lsb, int width, uint32_t value, uint32_t delay = 0);
    void pulse_drive();

    // Common external APIs: generic sample primitives.
    void stage_sample_pin(int pin, uint32_t delay = 0);
    void stage_sample_field(int lsb, int width, uint32_t delay = 0);
    void stage_sample_all(uint32_t delay = 0);
    void pulse_sample();

    uint64_t clock() const { return clock_; }
    uint64_t cycle() const { return cycle_; }
    uint8_t top_data() const { return top_data_; }
    void set_top_data(uint8_t data);
    uint8_t get_top_data();
    // Common external APIs: raw socket status for drive/sample event observation.
    uint32_t current_drive_alert_raw() const;
    std::vector<uint32_t> current_drive_counts_raw() const;
    uint32_t current_sample_alert_raw() const;
    std::vector<uint32_t> current_sample_counts_raw() const;

    // Common external APIs: per-pin decoded counters from DRIV_CNTS/SAMP_CNTS.
    uint32_t drive_count(int pin) const;
    uint32_t sample_count(int pin) const;
    std::vector<uint32_t> drive_counts() const;
    std::vector<uint32_t> sample_counts() const;

    uint32_t current_output_raw() const;
    bool current_compare_pass() const;
    bool current_compare_valid() const;
    uint32_t last_sampled_raw() const { return last_sample_.raw; }
    SampleRecord last_sampled_record() const { return last_sample_; }
    const std::vector<SampleRecord>& captured_samples() const { return captured_samples_; }
    std::vector<uint32_t> captured_raw_outputs() const;
    bool has_captured_samples() const { return !captured_samples_.empty(); }
    void clear_captured_samples();
    bool compare() const;

    // Common external APIs: helpers for decoding raw sampled bits in wrapper code.
    uint32_t extract_output_field(uint32_t raw, int lsb, int width) const;
    bool extract_output_bit(uint32_t raw, int bit) const;
    uint32_t extract_counter_field(const std::vector<uint32_t>& raw_counts,
                                   int pin,
                                   int pin_count) const;

    void print(const std::string& s) const;

private:
    // Internal helpers: reset/bootstrap and low-level socket staging.
    void init_reset_sequence_();
    void clear_driv_();
    void clear_samp_();
    void set_driv_pin_(int pin, bool value, uint32_t delay = 0);
    void set_driv_field_(int lsb, int width, uint32_t value, uint32_t delay = 0);
    void set_samp_pin_(int pin, uint32_t delay = 0);
    void set_samp_field_(int lsb, int width, uint32_t delay = 0);
    void enable_all_samples_(uint32_t delay = 0);
    void pulse_driv_();
    void pulse_samp_();
    void capture_sample_if_ready_();

    // Internal helpers: bounds checking and delay normalization.
    uint32_t clamp_offset_(uint32_t offset) const;
    void validate_pin_index_(int pin, int pin_count, const char* label) const;
    void validate_field_(int lsb, int width, int pin_count, const char* label) const;

    std::unique_ptr<VerilatedContext> contextp_;
    std::unique_ptr<VSocket> socketp_;
    std::unique_ptr<VerilatedVcdC> tfp_;

    uint64_t clock_ = 0;
    uint64_t cycle_ = 0;
    uint8_t top_data_ = 0;

    SampleRecord last_sample_{};
    std::vector<SampleRecord> captured_samples_;
};
