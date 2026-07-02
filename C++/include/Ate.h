#pragma once

#include "AteSocketConfig.h"
#include "Timing.h"
#include "VSocket.h"
#include "Waveform.h"
#include "verilated.h"

#ifdef ATE_ENABLE_TRACE
#include "verilated_vcd_c.h"
#endif

#include <array>
#include <cstdint>
#include <deque>
#include <memory>
#include <string>
#include <vector>

#ifdef ATE_PYBIND
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#endif

struct CompareSpec {
    enum class Mode {
        AllPins,
        SinglePin,
        Field
    };

    Mode mode = Mode::AllPins;
    int lsb = 0;
    int width = 1;
    uint32_t pin_delay = 0;
    uint32_t expected = 0;

    static CompareSpec all_pins(uint32_t pin_delay = 0, uint32_t expected = 0) {
        CompareSpec spec;
        spec.mode = Mode::AllPins;
        spec.width = 1;
        spec.pin_delay = pin_delay;
        spec.expected = expected;
        return spec;
    }

    static CompareSpec single_pin(int pin, uint32_t pin_delay = 0, uint32_t expected = 0) {
        CompareSpec spec;
        spec.mode = Mode::SinglePin;
        spec.lsb = pin;
        spec.width = 1;
        spec.pin_delay = pin_delay;
        spec.expected = expected;
        return spec;
    }

    static CompareSpec field(int lsb, int width, uint32_t pin_delay = 0, uint32_t expected = 0) {
        CompareSpec spec;
        spec.mode = Mode::Field;
        spec.lsb = lsb;
        spec.width = width;
        spec.pin_delay = pin_delay;
        spec.expected = expected;
        return spec;
    }
};

struct SampleRecord {
    // Cycle index when the sample alert was observed.
    uint64_t cycle = 0;
    // Output-pin mask that actually asserted SAMP_ALERT on this cycle.
    uint32_t sample_mask = 0;
    // Raw packed SAMP_OUT value captured from the socket.
    uint32_t raw = 0;
    // TOP_DATA value that was present when this sample was captured.
    uint32_t top_data_snapshot = 0;
    // Compare rule that was active when this sample was requested.
    CompareSpec compare_spec = CompareSpec{};
};

struct InputPinConfig {
    int lsb = 0;
    int width = 1;
    DriveWaveform waveform = DriveWaveform::nrz();
    uint32_t default_value = 0;
};

struct OutputPinConfig {
    int lsb = 0;
    int width = 1;
    uint32_t default_value = 0;
};

class ATE {
public:
    // Socket geometry is generated from pinmap/config so the ATE engine does
    // not silently bake in one DUT's pin shape.
    static constexpr int kOffsetWidth = AteSocketConfig::kOffsetWidth;
    static constexpr int kDelayWidth = 32;
    static constexpr int kPinInCount = AteSocketConfig::kPinInCount;
    static constexpr int kPinOutCount = AteSocketConfig::kPinOutCount;

    explicit ATE(std::string wave_name = {},
                 bool trace_enable = true,
                 uint32_t top_data_init = 0);

    ~ATE();

    // Common external APIs: basic simulation lifecycle.
    void tick();
    void advance_phase();
    void advance_to_phase(uint64_t target_phase);
    void advance_period();
    void run_cycles(uint32_t cycles);
    void reset();

    // Common external APIs: cycle/phase timing set.
    void set_timing(const TimingSet& timing);
    TimingSet timing() const { return timing_; }
    uint64_t phase() const { return phase_; }
    uint32_t phase_in_period() const { return phase_in_period_; }

    // Common external APIs: vector-row waveform binding. Pins get their
    // waveform behavior from schema/configuration, not from special pin names.
    void bind_drive_pin_wave(int pin,
                             bool value,
                             DriveWaveform waveform,
                             uint32_t pin_delay = 0);
    void bind_drive_field_wave(int lsb,
                               int width,
                               uint32_t value,
                               DriveWaveform waveform,
                               uint32_t pin_delay = 0);
    void bind_nrz_drive(int pin, bool value, uint32_t pin_delay = 0);
    void bind_rzz_drive(int pin, DriveWaveform waveform = DriveWaveform::rzz());
    void clear_rzz_drive(int pin);
    void clear_rzz_drives();

    // Common external APIs: vector-row input pin schema.
    void clear_input_pin_configs();
    void configure_input_pin(int lsb,
                             int width,
                             DriveWaveform waveform,
                             uint32_t default_value = 0);
    void load_vector_row_defaults();
    void begin_vector_row();
    void activate_input_pin(int pin, uint32_t pin_delay = 0);
    void set_input_field(int lsb, int width, uint32_t value, uint32_t pin_delay = 0);
    void commit_vector_row();
    void schedule_input_pin_at(uint64_t due_phase,
                               int pin,
                               bool value,
                               uint32_t pin_delay = 0,
                               uint32_t hold_duration = 0,
                               bool update_nrz_stable = false,
                               bool default_value_event = false);
    void schedule_input_field_at(uint64_t due_phase,
                                 int lsb,
                                 int width,
                                 uint32_t value,
                                 uint32_t pin_delay = 0,
                                 uint32_t hold_duration = 0,
                                 bool update_nrz_stable = false,
                                 bool default_value_event = false);

    // Common external APIs: vector-row output pin schema.
    void clear_output_pin_configs();
    void configure_output_pin(int lsb, int width, uint32_t default_value = 0);
    void expect_output_field(int lsb, int width, uint32_t expected, uint32_t pin_delay = 0);
    void schedule_output_field_at(uint64_t due_phase,
                                  int lsb,
                                  int width,
                                  uint32_t expected,
                                  uint32_t pin_delay = 0);

    // Common external APIs: clear currently staged drive/sample commands
    // before building the next custom operation.
    void clear_drive();
    void clear_sample();

    // Common external APIs: generic drive primitives for direct low-level tests.
    void stage_drive_pin_wave(int pin,
                              bool value,
                              DriveWaveform waveform,
                              uint32_t pin_delay = 0);
    void stage_drive_field_wave(int lsb,
                                int width,
                                uint32_t value,
                                DriveWaveform waveform,
                                uint32_t pin_delay = 0);
    void pulse_drive();
    void pulse_alert();
    void schedule_alert_at(uint64_t due_phase);

    // Common external APIs: sample first, then compare the saved sample history.
    void sample();
    void sample(const CompareSpec& spec);
    bool compare_last();
    bool compare_all();
    std::vector<bool> compare_results() const;
    bool has_compare_results() const { return !compare_results_.empty(); }
    bool last_compare_result() const;
    bool all_compare_results_pass() const;
    void clear_compare_results();
    void print_compare_results() const;
    void print_compare_results_and() const;
    void print_sample_records() const;

    uint64_t clock() const { return clock_; }
    uint64_t cycle() const { return cycle_; }
    uint32_t top_data() const { return top_data_; }
    void set_top_data(uint32_t data);
    uint32_t get_top_data();
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
    uint32_t last_sampled_raw() const { return last_sample_.raw; }
    SampleRecord last_sampled_record() const { return last_sample_; }
    const std::vector<SampleRecord>& captured_samples() const { return captured_samples_; }
    std::vector<uint32_t> captured_raw_outputs() const;
    bool has_captured_samples() const { return !captured_samples_.empty(); }
    void clear_captured_samples();
    // Common external APIs: helpers for decoding raw sampled bits in wrapper code.
    uint32_t extract_output_field(uint32_t raw, int lsb, int width) const;
    bool extract_output_bit(uint32_t raw, int bit) const;
    uint32_t extract_counter_field(const std::vector<uint32_t>& raw_counts,
                                   int pin,
                                   int pin_count) const;

    void print(const std::string& s) const;

private:
    struct ScheduledDriveEvent {
        uint64_t due_phase = 0;
        int pin = 0;
        bool value = false;
        uint32_t pin_delay = 0;
        uint32_t hold_duration = 0;
        bool update_nrz_stable = false;
        bool default_value_event = false;
    };

    struct ScheduledSampleEvent {
        uint64_t due_phase = 0;
        CompareSpec spec = CompareSpec{};
    };

    struct PendingCompareSpec {
        // Compare specs that share one scheduled sample phase belong to the
        // same capture group. This lets one hardware SAMP_ALERT satisfy
        // multi-pin samples from a single vector row, while preventing later
        // delayed rows from being consumed by the first alert.
        uint64_t group = 0;
        CompareSpec spec = CompareSpec{};
    };

    // Internal helpers: reset/bootstrap and low-level socket staging.
    void init_reset_sequence_();
    void clear_driv_();
    void clear_samp_();
    void set_driv_pin_(int pin, bool value, uint32_t pin_delay = 0, uint32_t hold_duration = 0);
    void set_driv_field_(int lsb, int width, uint32_t value, uint32_t pin_delay = 0, uint32_t hold_duration = 0);
    void set_samp_pin_(int pin, uint32_t pin_delay = 0);
    void set_samp_field_(int lsb, int width, uint32_t pin_delay = 0);
    void enable_all_samples_(uint32_t pin_delay = 0);
    void pulse_driv_();
    void pulse_samp_();
    void capture_sample_if_ready_();
    void schedule_drive_event_(uint64_t due_phase,
                               int pin,
                               bool value,
                               uint32_t pin_delay = 0,
                               uint32_t hold_duration = 0,
                               bool update_nrz_stable = false,
                               bool default_value_event = false);
    void schedule_nrz_pending_drives_();
    void schedule_rzz_bound_drives_();
    void execute_scheduled_drive_events_();
    bool has_scheduled_nrz_stable_event_(int pin) const;
    void schedule_sample_event_(uint64_t due_phase, const CompareSpec& spec);
    void execute_scheduled_sample_events_();
    void schedule_alert_event_(uint64_t due_phase);
    void execute_scheduled_alert_events_();
    uint64_t phase_with_offset_(uint64_t row_start_phase,
                                uint32_t waveform_phase,
                                int32_t base_phase,
                                const char* label) const;
    const InputPinConfig& input_pin_config_(int lsb, int width) const;
    const OutputPinConfig& output_pin_config_(int lsb, int width) const;
    uint32_t aligned_compare_value_(const CompareSpec& spec) const;
    uint32_t compare_mask_(const CompareSpec& spec) const;
    bool sample_matches_(const SampleRecord& sample) const;
    void validate_compare_spec_(const CompareSpec& spec) const;

    // Internal helpers: bounds checking.
    void validate_pin_index_(int pin, int pin_count, const char* label) const;
    void validate_field_(int lsb, int width, int pin_count, const char* label) const;

    std::unique_ptr<VerilatedContext> contextp_;
    std::unique_ptr<VSocket> socketp_;
#ifdef ATE_ENABLE_TRACE
    std::unique_ptr<VerilatedVcdC> tfp_;
#endif

    uint64_t clock_ = 0;
    uint64_t phase_ = 0;
    uint64_t cycle_ = 0;
    uint32_t phase_in_period_ = 0;
    uint32_t top_data_ = 0;
    TimingSet timing_{};
    uint32_t nrz_drive_mask_ = 0;
    uint32_t nrz_drive_values_ = 0;
    uint32_t nrz_pending_mask_ = 0;
    uint32_t nrz_pending_values_ = 0;
    std::array<uint32_t, kPinInCount> nrz_pending_pin_delays_{};
    std::array<bool, kPinInCount> nrz_pending_default_flags_{};
    std::deque<ScheduledDriveEvent> scheduled_drive_events_;
    std::deque<ScheduledSampleEvent> scheduled_sample_events_;
    std::deque<uint64_t> scheduled_alert_events_;
    uint32_t rzz_drive_mask_ = 0;
    uint32_t rzz_default_values_ = 0;
    bool loading_vector_defaults_ = false;
    std::vector<InputPinConfig> input_pin_configs_;
    std::vector<OutputPinConfig> output_pin_configs_;
    std::deque<PendingCompareSpec> pending_compare_specs_;

    SampleRecord last_sample_{};
    std::vector<SampleRecord> captured_samples_;
    std::vector<uint8_t> compare_results_;
};
