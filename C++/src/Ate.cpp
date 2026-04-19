#include "Ate.h"

#include <cstddef>
#include <iostream>
#include <stdexcept>
#include <type_traits>

namespace {

constexpr uint32_t kCompareMask = (1U << ATE::kPinOutCount) - 1U;

uint32_t fieldMask(int width) {
    if (width >= 32) {
        return 0xffffffffU;
    }
    return (1U << width) - 1U;
}

// Internal utility helpers for manipulating Verilator packed buses.
template <typename WideBus>
void clearWideBus(WideBus& bus) {
    if constexpr (std::is_integral_v<WideBus>) {
        bus = 0;
    } else {
        constexpr std::size_t kWords = sizeof(WideBus) / sizeof(WData);
        for (std::size_t i = 0; i < kWords; ++i) {
            bus[i] = 0;
        }
    }
}

template <typename WideBus>
void setWideBit(WideBus& bus, int bit, bool value) {
    if constexpr (std::is_integral_v<WideBus>) {
        const WideBus mask = static_cast<WideBus>(1) << bit;
        if (value) {
            bus |= mask;
        } else {
            bus &= ~mask;
        }
    } else {
        const std::size_t word = static_cast<std::size_t>(bit / 32);
        const int offset = bit % 32;
        const WData mask = static_cast<WData>(1U) << offset;
        if (value) {
            bus[word] |= mask;
        } else {
            bus[word] &= ~mask;
        }
    }
}

template <typename WideBus>
void setWideField(WideBus& bus, int lsb, int width, uint32_t value) {
    for (int i = 0; i < width; ++i) {
        setWideBit(bus, lsb + i, ((value >> i) & 1U) != 0U);
    }
}

template <typename WideBus>
std::vector<uint32_t> wideBusToWords(const WideBus& bus) {
    std::vector<uint32_t> words;
    if constexpr (std::is_integral_v<WideBus>) {
        words.push_back(static_cast<uint32_t>(bus));
    } else {
        constexpr std::size_t kWords = sizeof(WideBus) / sizeof(WData);
        words.reserve(kWords);
        for (std::size_t i = 0; i < kWords; ++i) {
            words.push_back(static_cast<uint32_t>(bus[i]));
        }
    }
    return words;
}

void setScalarBit(uint32_t& bus, int bit, bool value) {
    const uint32_t mask = 1U << bit;
    if (value) {
        bus |= mask;
    } else {
        bus &= ~mask;
    }
}

}  // namespace

// Public constructor: create the socket model, optionally enable waveform dump,
// and bring the DUT into a clean reset state.
ATE::ATE(std::string wave_name, bool trace_enable, uint32_t top_data_init)
    : contextp_(std::make_unique<VerilatedContext>()),
      socketp_(nullptr),
      top_data_(top_data_init) {
    contextp_->traceEverOn(trace_enable);
    socketp_ = std::make_unique<VSocket>(contextp_.get(), "TOP");

    if (trace_enable && !wave_name.empty()) {
        tfp_ = std::make_unique<VerilatedVcdC>();
        socketp_->trace(tfp_.get(), 99);
        tfp_->open(wave_name.c_str());
    }

    socketp_->ATE_CLK = 0;
    socketp_->ATE_RST_N = 0;
    socketp_->ALERT = 0;
    clear_driv_();
    clear_samp_();
    bind_rzz_drive(kClockPin);

    init_reset_sequence_();
}

ATE::~ATE() {
    if (tfp_) {
        tfp_->close();
    }
    if (socketp_) {
        socketp_->final();
    }
}

// Internal bootstrap reset used only during construction.
void ATE::init_reset_sequence_() {
    drive_reset_pin_(false);
    advance_phase();
    advance_phase();

    socketp_->ATE_RST_N = 0;
    for (int i = 0; i < 8; ++i) {
        advance_phase();
    }

    socketp_->ATE_RST_N = 1;
    drive_reset_pin_(true);
    advance_phase();
    advance_phase();

    clear_captured_samples();
    clear_compare_results();
    pending_compare_specs_.clear();
    nrz_drive_mask_ = 1U << kResetPin;
    nrz_drive_values_ = 1U << kResetPin;
    nrz_pending_mask_ = 0;
    nrz_pending_values_ = 0;
    cycle_ = 0;
    phase_in_period_ = 0;
}

// Public reset entry. Wrapper code can call this to restart a test sequence.
void ATE::reset() {
    socketp_->ATE_RST_N = 0;
    socketp_->ALERT = 0;
    clear_driv_();
    clear_samp_();
    nrz_drive_mask_ = 0;
    nrz_drive_values_ = 0;
    nrz_pending_mask_ = 0;
    nrz_pending_values_ = 0;
    drive_reset_pin_(false);

    advance_phase();
    advance_phase();

    socketp_->ATE_RST_N = 1;
    drive_reset_pin_(true);
    advance_phase();
    advance_phase();

    clear_captured_samples();
    clear_compare_results();
    pending_compare_specs_.clear();
    nrz_drive_mask_ = 1U << kResetPin;
    nrz_drive_values_ = 1U << kResetPin;
    nrz_pending_mask_ = 0;
    nrz_pending_values_ = 0;
    cycle_ = 0;
    phase_in_period_ = 0;
}

// Compatibility alias: one ATE phase, not one DUT clock period.
void ATE::tick() {
    advance_phase();
}

// Public single-phase advance. This is the base timing primitive for all custom flows.
void ATE::advance_phase() {
    apply_nrz_drives_();
    apply_rzz_drives_();

    socketp_->ATE_CLK = 0;
    socketp_->eval();
    if (tfp_) {
        tfp_->dump(clock_++);
    }

    socketp_->ATE_CLK = 1;
    socketp_->eval();
    capture_sample_if_ready_();
    if (tfp_) {
        tfp_->dump(clock_++);
    }

    clear_driv_();
    clear_samp_();
    ++phase_;
    phase_in_period_ = (phase_in_period_ + 1U) % timing_.period_phases;
}

// Public full timing-period advance. This is the vector-cycle primitive.
void ATE::advance_period() {
    for (uint32_t i = 0; i < timing_.period_phases; ++i) {
        advance_phase();
    }
    ++cycle_;
}

// Public convenience helper for advancing multiple vector periods.
void ATE::run_cycles(uint32_t cycles) {
    for (uint32_t i = 0; i < cycles; ++i) {
        advance_period();
    }
}

void ATE::set_timing(const TimingSet& timing) {
    validate_timing_set(timing);
    timing_ = timing;
    phase_in_period_ %= timing_.period_phases;
}

void ATE::bind_rzz_drive(int pin, DriveWaveform waveform) {
    validate_pin_index_(pin, kPinInCount, "RZZ drive pin");
    if (waveform.kind != DriveWaveformKind::RZZ) {
        throw std::invalid_argument("bind_rzz_drive requires an RZZ waveform");
    }

    const uint32_t mask = 1U << pin;
    rzz_drive_mask_ |= mask;
    if (waveform.default_value) {
        rzz_default_values_ |= mask;
    } else {
        rzz_default_values_ &= ~mask;
    }
}

void ATE::clear_rzz_drive(int pin) {
    validate_pin_index_(pin, kPinInCount, "RZZ drive pin");
    const uint32_t mask = 1U << pin;
    rzz_drive_mask_ &= ~mask;
    rzz_default_values_ &= ~mask;
}

void ATE::clear_rzz_drives() {
    rzz_drive_mask_ = 0;
    rzz_default_values_ = 0;
}

void ATE::clear_input_pin_configs() {
    input_pin_configs_.clear();
}

void ATE::configure_input_pin(int lsb,
                              int width,
                              DriveWaveform waveform,
                              uint32_t default_value) {
    validate_field_(lsb, width, kPinInCount, "input pin config");
    if (width < 32 && (default_value & ~fieldMask(width)) != 0U) {
        throw std::invalid_argument("input pin default value does not fit field width");
    }

    for (const auto& config : input_pin_configs_) {
        const int config_end = config.lsb + config.width;
        const int new_end = lsb + width;
        if (lsb < config_end && config.lsb < new_end) {
            throw std::invalid_argument("input pin config overlaps an existing field");
        }
    }

    input_pin_configs_.push_back(InputPinConfig{
        .lsb = lsb,
        .width = width,
        .waveform = waveform,
        .default_value = default_value,
    });
}

void ATE::begin_vector_row() {
    clear_drive();
    clear_rzz_drives();

    for (const auto& config : input_pin_configs_) {
        stage_drive_field_wave(config.lsb,
                               config.width,
                               config.default_value,
                               config.waveform);
    }
}

void ATE::activate_input_pin(int pin) {
    const auto& config = input_pin_config_(pin, 1);
    if (config.width != 1) {
        throw std::invalid_argument("activate_input_pin requires a single-bit pin config");
    }
    if (config.waveform.kind == DriveWaveformKind::RZZ) {
        throw std::invalid_argument("activate_input_pin does not support RZZ pins");
    }
    const bool default_value = (config.default_value & 1U) != 0U;
    stage_drive_pin_wave(pin, !default_value, config.waveform);
}

void ATE::set_input_field(int lsb, int width, uint32_t value) {
    const auto& config = input_pin_config_(lsb, width);
    if (config.waveform.kind == DriveWaveformKind::RZZ) {
        throw std::invalid_argument("set_input_field does not support RZZ pins");
    }
    if (width < 32 && (value & ~fieldMask(width)) != 0U) {
        throw std::invalid_argument("input field value does not fit field width");
    }
    stage_drive_field_wave(lsb, width, value, config.waveform);
}

void ATE::commit_vector_row() {
    pulse_drive();
}

void ATE::clear_output_pin_configs() {
    output_pin_configs_.clear();
}

void ATE::configure_output_pin(int lsb, int width, uint32_t default_value) {
    validate_field_(lsb, width, kPinOutCount, "output pin config");
    if (width < 32 && (default_value & ~fieldMask(width)) != 0U) {
        throw std::invalid_argument("output pin default value does not fit field width");
    }

    for (const auto& config : output_pin_configs_) {
        const int config_end = config.lsb + config.width;
        const int new_end = lsb + width;
        if (lsb < config_end && config.lsb < new_end) {
            throw std::invalid_argument("output pin config overlaps an existing field");
        }
    }

    output_pin_configs_.push_back(OutputPinConfig{
        .lsb = lsb,
        .width = width,
        .default_value = default_value,
    });
}

void ATE::expect_output_field(int lsb, int width, uint32_t expected) {
    const auto& config = output_pin_config_(lsb, width);
    if (width < 32 && (expected & ~fieldMask(width)) != 0U) {
        throw std::invalid_argument("output field expected value does not fit field width");
    }
    set_top_data(expected);
    sample(CompareSpec::field(config.lsb, config.width, 0));
}

// Public convenience helper: discard the currently staged drive operation.
void ATE::clear_drive() {
    clear_driv_();
    nrz_pending_mask_ = 0;
    nrz_pending_values_ = 0;
}

// Public convenience helper: discard the currently staged sample operation.
void ATE::clear_sample() {
    clear_samp_();
}

// Public drive primitive for one input pin.
void ATE::stage_drive_pin(int pin, bool value, uint32_t delay) {
    stage_drive_pin_wave(pin, value, DriveWaveform::nrz(), delay);
}

void ATE::stage_drive_field(int lsb, int width, uint32_t value, uint32_t delay) {
    stage_drive_field_wave(lsb, width, value, DriveWaveform::nrz(), delay);
}

void ATE::stage_drive_pin_wave(int pin,
                               bool value,
                               DriveWaveform waveform,
                               uint32_t delay) {
    validate_pin_index_(pin, kPinInCount, "drive pin");

    switch (waveform.kind) {
    case DriveWaveformKind::NRZ: {
        const uint32_t mask = 1U << pin;
        nrz_pending_mask_ |= mask;
        if (value) {
            nrz_pending_values_ |= mask;
        } else {
            nrz_pending_values_ &= ~mask;
        }
        return;
    }
    case DriveWaveformKind::RZZ:
        bind_rzz_drive(pin, DriveWaveform::rzz(value));
        return;
    }
}

void ATE::stage_drive_field_wave(int lsb,
                                 int width,
                                 uint32_t value,
                                 DriveWaveform waveform,
                                 uint32_t delay) {
    validate_field_(lsb, width, kPinInCount, "drive field");

    switch (waveform.kind) {
    case DriveWaveformKind::NRZ:
        for (int i = 0; i < width; ++i) {
            const int pin = lsb + i;
            const uint32_t mask = 1U << pin;
            nrz_pending_mask_ |= mask;
            if (((value >> i) & 1U) != 0U) {
                nrz_pending_values_ |= mask;
            } else {
                nrz_pending_values_ &= ~mask;
            }
        }
        return;
    case DriveWaveformKind::RZZ:
        for (int i = 0; i < width; ++i) {
            const bool default_bit = ((value >> i) & 1U) != 0U;
            bind_rzz_drive(lsb + i, DriveWaveform::rzz(default_bit));
        }
        return;
    }
}

// Public execute step for the staged drive request.
void ATE::pulse_drive() {
    pulse_driv_();
}

void ATE::pulse_alert() {
    socketp_->ALERT = 1;
    begin_vector_row();
    commit_vector_row();
    socketp_->ALERT = 0;
}

void ATE::sample() {
    sample(CompareSpec{});
}

// Run one sample operation through the hardware sampler. Delay belongs here.
void ATE::sample(const CompareSpec& spec) {
    validate_compare_spec_(spec);

    pending_compare_specs_.push_back(spec);
    clear_samp_();
    switch (spec.mode) {
    case CompareSpec::Mode::AllPins:
        enable_all_samples_(timing_.sample_phase + spec.delay);
        break;
    case CompareSpec::Mode::SinglePin:
        set_samp_pin_(spec.lsb, timing_.sample_phase + spec.delay);
        break;
    case CompareSpec::Mode::Field:
        set_samp_field_(spec.lsb, spec.width, timing_.sample_phase + spec.delay);
        break;
    }
    pulse_samp_();
}

bool ATE::compare_last() {
    if (!has_captured_samples()) {
        compare_results_.push_back(0U);
        return false;
    }

    const bool pass = sample_matches_(captured_samples_.back());
    compare_results_.push_back(pass ? 1U : 0U);
    return pass;
}

bool ATE::compare_all() {
    if (!has_captured_samples()) {
        compare_results_.push_back(0U);
        return false;
    }

    bool all_pass = true;
    for (const auto& sample : captured_samples_) {
        const bool pass = sample_matches_(sample);
        compare_results_.push_back(pass ? 1U : 0U);
        if (!pass) {
            all_pass = false;
        }
    }
    return all_pass;
}

// Public helper for updating the compare reference data presented to Comparer.
void ATE::set_top_data(uint32_t data) {
    top_data_ = data & kCompareMask;
}

uint32_t ATE::get_top_data() {
    return top_data_;
}

// Public raw view of which input pins generated a drive event on the current cycle.
uint32_t ATE::current_drive_alert_raw() const {
    return socketp_->DRIV_ALERT;
}

// Public raw view of the packed per-pin drive counters maintained by PinInRegister.
std::vector<uint32_t> ATE::current_drive_counts_raw() const {
    return wideBusToWords(socketp_->DRIV_CNTS);
}

// Public raw view of which output pins generated a sample event on the current cycle.
uint32_t ATE::current_sample_alert_raw() const {
    return socketp_->SAMP_ALERT;
}

// Public raw view of the packed per-pin sample counters maintained by PinOutRegister.
std::vector<uint32_t> ATE::current_sample_counts_raw() const {
    return wideBusToWords(socketp_->SAMP_CNTS);
}

// Public helper for reading one pin's drive count from the packed DRIV_CNTS bus.
uint32_t ATE::drive_count(int pin) const {
    validate_pin_index_(pin, kPinInCount, "drive count pin");
    return extract_counter_field(current_drive_counts_raw(), pin, kPinInCount);
}

// Public helper for reading one pin's sample count from the packed SAMP_CNTS bus.
uint32_t ATE::sample_count(int pin) const {
    validate_pin_index_(pin, kPinOutCount, "sample count pin");
    return extract_counter_field(current_sample_counts_raw(), pin, kPinOutCount);
}

// Public helper for wrappers that want all per-pin drive counters at once.
std::vector<uint32_t> ATE::drive_counts() const {
    std::vector<uint32_t> counts;
    counts.reserve(kPinInCount);
    for (int pin = 0; pin < kPinInCount; ++pin) {
        counts.push_back(drive_count(pin));
    }
    return counts;
}

// Public helper for wrappers that want all per-pin sample counters at once.
std::vector<uint32_t> ATE::sample_counts() const {
    std::vector<uint32_t> counts;
    counts.reserve(kPinOutCount);
    for (int pin = 0; pin < kPinOutCount; ++pin) {
        counts.push_back(sample_count(pin));
    }
    return counts;
}

// Public raw view of the current output bus without creating a sample event.
uint32_t ATE::current_output_raw() const {
    return socketp_->SAMP_OUT;
}

// Public helper for wrapper code that only wants raw sample values.
std::vector<uint32_t> ATE::captured_raw_outputs() const {
    std::vector<uint32_t> values;
    values.reserve(captured_samples_.size());
    for (const auto& sample : captured_samples_) {
        values.push_back(sample.raw);
    }
    return values;
}

// Public cleanup for all captured sample history.
void ATE::clear_captured_samples() {
    last_sample_ = {};
    captured_samples_.clear();
}

std::vector<bool> ATE::compare_results() const {
    std::vector<bool> results;
    results.reserve(compare_results_.size());
    for (uint8_t result : compare_results_) {
        results.push_back(result != 0U);
    }
    return results;
}

bool ATE::last_compare_result() const {
    if (!has_compare_results()) {
        return false;
    }
    return compare_results_.back() != 0U;
}

bool ATE::all_compare_results_pass() const {
    if (!has_compare_results()) {
        return false;
    }

    for (uint8_t result : compare_results_) {
        if (result == 0U) {
            return false;
        }
    }
    return true;
}

void ATE::clear_compare_results() {
    compare_results_.clear();
}

void ATE::print_compare_results() const {
    for (uint8_t result : compare_results_) {
        std::cout << (result != 0U ? "*" : ".");
    }
    std::cout << std::flush;
}

void ATE::print_compare_results_and() const {
    std::cout << (all_compare_results_pass() ? "*" : ".") << std::flush;
}

// Public decoder helper for customer wrappers.
uint32_t ATE::extract_output_field(uint32_t raw, int lsb, int width) const {
    validate_field_(lsb, width, 32, "output field");
    if (width == 32) {
        return raw;
    }
    return (raw >> lsb) & ((1U << width) - 1U);
}

// Public decoder helper for customer wrappers.
bool ATE::extract_output_bit(uint32_t raw, int bit) const {
    validate_pin_index_(bit, 32, "output bit");
    return ((raw >> bit) & 1U) != 0U;
}

// Public decoder helper for packed per-pin counter buses such as DRIV_CNTS/SAMP_CNTS.
uint32_t ATE::extract_counter_field(const std::vector<uint32_t>& raw_counts,
                                    int pin,
                                    int pin_count) const {
    validate_pin_index_(pin, pin_count, "counter pin");

    const int lsb = pin * kOffsetWidth;
    const std::size_t word_index = static_cast<std::size_t>(lsb / 32);
    const int bit_index = lsb % 32;

    if (word_index >= raw_counts.size()) {
        throw std::out_of_range("counter raw data out of range");
    }

    if (bit_index <= 32 - kOffsetWidth) {
        return extract_output_field(raw_counts[word_index], bit_index, kOffsetWidth);
    }

    const uint32_t low = raw_counts[word_index] >> bit_index;
    const uint32_t high_width = kOffsetWidth - (32 - bit_index);
    const uint32_t high =
        (word_index + 1 < raw_counts.size()) ? extract_output_field(raw_counts[word_index + 1], 0, high_width) : 0;
    return (high << (32 - bit_index)) | low;
}

void ATE::print(const std::string& s) const {
    std::cout << s << std::endl;
}

// Internal low-level socket clear. External code should prefer clear_drive().
void ATE::clear_driv_() {
    socketp_->DRIV = 0;
    socketp_->DRIV_IN = 0;
    clearWideBus(socketp_->DRIV_OFFSET);
}

// Internal low-level socket clear. External code should prefer clear_sample().
void ATE::clear_samp_() {
    socketp_->SAMP = 0;
    clearWideBus(socketp_->SAMP_OFFSET);
}

// Internal staging helper used by the public drive APIs after validation.
void ATE::set_driv_pin_(int pin, bool value, uint32_t delay) {
    uint32_t driv = socketp_->DRIV;
    uint32_t driv_in = socketp_->DRIV_IN;

    setScalarBit(driv, pin, true);
    setScalarBit(driv_in, pin, value);

    socketp_->DRIV = driv;
    socketp_->DRIV_IN = driv_in;
    setWideField(socketp_->DRIV_OFFSET,
                 pin * kOffsetWidth,
                 kOffsetWidth,
                 clamp_offset_(delay));
}

// Internal staging helper used by the public drive APIs after validation.
void ATE::set_driv_field_(int lsb, int width, uint32_t value, uint32_t delay) {
    for (int i = 0; i < width; ++i) {
        set_driv_pin_(lsb + i, ((value >> i) & 1U) != 0U, delay);
    }
}

// Internal staging helper used by the public sample APIs after validation.
void ATE::set_samp_pin_(int pin, uint32_t delay) {
    const uint32_t clamped_delay = clamp_offset_(delay);
    socketp_->SAMP |= (1U << pin);
    setWideField(socketp_->SAMP_OFFSET,
                 pin * kOffsetWidth,
                 kOffsetWidth,
                 clamped_delay);
}

// Internal staging helper used by the public sample APIs after validation.
void ATE::set_samp_field_(int lsb, int width, uint32_t delay) {
    for (int i = 0; i < width; ++i) {
        set_samp_pin_(lsb + i, delay);
    }
}

// Internal helper for stage_sample_all().
void ATE::enable_all_samples_(uint32_t delay) {
    for (int pin = 0; pin < kPinOutCount; ++pin) {
        set_samp_pin_(pin, delay);
    }
}

// Internal pulse wrapper. External code should prefer pulse_drive().
void ATE::pulse_driv_() {
    advance_period();
}

// Internal pulse wrapper. External code should prefer pulse_sample().
void ATE::pulse_samp_() {
    advance_period();
}

void ATE::apply_nrz_drives_() {
    if (phase_in_period_ >= timing_.nrz_rise_phase && nrz_pending_mask_ != 0U) {
        nrz_drive_values_ = (nrz_drive_values_ & ~nrz_pending_mask_) |
                            (nrz_pending_values_ & nrz_pending_mask_);
        nrz_drive_mask_ |= nrz_pending_mask_;
        nrz_pending_mask_ = 0;
        nrz_pending_values_ = 0;
    }

    for (int pin = 0; pin < kPinInCount; ++pin) {
        const uint32_t mask = 1U << pin;
        if ((nrz_drive_mask_ & mask) != 0U) {
            set_driv_pin_(pin, (nrz_drive_values_ & mask) != 0U, 0);
        }
    }
}

// Internal periodic RZZ waveform driver. Bound pins are driven to their default
// value outside rzz_rise_phase/rzz_fall_phase and inverted inside it.
void ATE::apply_rzz_drives_() {
    const bool active =
        phase_in_period_ >= timing_.rzz_rise_phase &&
        phase_in_period_ < timing_.rzz_fall_phase;

    for (int pin = 0; pin < kPinInCount; ++pin) {
        const uint32_t mask = 1U << pin;
        if ((rzz_drive_mask_ & mask) == 0U) {
            continue;
        }
        const bool default_value = (rzz_default_values_ & mask) != 0U;
        const bool value = active ? !default_value : default_value;
        set_driv_pin_(pin, value, 0);
    }
}

void ATE::drive_reset_pin_(bool value) {
    const uint32_t mask = 1U << kResetPin;
    nrz_drive_mask_ |= mask;
    if (value) {
        nrz_drive_values_ |= mask;
    } else {
        nrz_drive_values_ &= ~mask;
    }
    nrz_pending_mask_ &= ~mask;
    nrz_pending_values_ &= ~mask;
}

const InputPinConfig& ATE::input_pin_config_(int lsb, int width) const {
    for (const auto& config : input_pin_configs_) {
        if (config.lsb == lsb && config.width == width) {
            return config;
        }
    }
    throw std::invalid_argument("input pin config not found");
}

const OutputPinConfig& ATE::output_pin_config_(int lsb, int width) const {
    for (const auto& config : output_pin_configs_) {
        if (config.lsb == lsb && config.width == width) {
            return config;
        }
    }
    throw std::invalid_argument("output pin config not found");
}

// Internal sample capture path. It records only what the hardware actually reports.
void ATE::capture_sample_if_ready_() {
    if (socketp_->SAMP_ALERT == 0) {
        return;
    }

    CompareSpec captured_spec{};
    if (!pending_compare_specs_.empty()) {
        captured_spec = pending_compare_specs_.front();
        pending_compare_specs_.pop_front();
    }

    last_sample_.cycle = cycle_;
    last_sample_.sample_mask = socketp_->SAMP_ALERT;
    last_sample_.raw = socketp_->SAMP_OUT;
    last_sample_.top_data_snapshot = aligned_compare_value_(captured_spec);
    last_sample_.compare_spec = captured_spec;
    captured_samples_.push_back(last_sample_);
}

// Build the bit-mask that a compare request requires the sample to cover.
uint32_t ATE::aligned_compare_value_(const CompareSpec& spec) const {
    switch (spec.mode) {
    case CompareSpec::Mode::AllPins:
        return top_data_ & kCompareMask;
    case CompareSpec::Mode::SinglePin:
        return ((top_data_ & 1U) << spec.lsb) & kCompareMask;
    case CompareSpec::Mode::Field:
        return ((top_data_ & fieldMask(spec.width)) << spec.lsb) & kCompareMask;
    }

    return top_data_ & kCompareMask;
}

// Build the bit-mask that a compare request requires the sample to cover.
uint32_t ATE::compare_mask_(const CompareSpec& spec) const {
    switch (spec.mode) {
    case CompareSpec::Mode::AllPins:
        return kCompareMask;
    case CompareSpec::Mode::SinglePin:
        return (1U << spec.lsb) & kCompareMask;
    case CompareSpec::Mode::Field:
        return (fieldMask(spec.width) << spec.lsb) & kCompareMask;
    }

    return kCompareMask;
}

// Match one saved sample against the TOP_DATA snapshot and compare rule captured with it.
bool ATE::sample_matches_(const SampleRecord& sample) const {
    const uint32_t requested_mask = compare_mask_(sample.compare_spec);
    if ((sample.sample_mask & requested_mask) != requested_mask) {
        return false;
    }

    return (sample.raw & requested_mask) == (sample.top_data_snapshot & requested_mask);
}

// Validate compare request parameters before sampling or replaying history.
void ATE::validate_compare_spec_(const CompareSpec& spec) const {
    switch (spec.mode) {
    case CompareSpec::Mode::AllPins:
        break;
    case CompareSpec::Mode::SinglePin:
        validate_pin_index_(spec.lsb, kPinOutCount, "compare pin");
        break;
    case CompareSpec::Mode::Field:
        validate_field_(spec.lsb, spec.width, kPinOutCount, "compare field");
        break;
    }
}

// Internal delay normalization so wrappers can pass values larger than the hardware limit safely.
uint32_t ATE::clamp_offset_(uint32_t offset) const {
    return offset > kMaxOffset ? kMaxOffset : offset;
}

// Internal argument validation for public pin APIs.
void ATE::validate_pin_index_(int pin, int pin_count, const char* label) const {
    if (pin < 0 || pin >= pin_count) {
        throw std::out_of_range(std::string(label) + " out of range");
    }
}

// Internal argument validation for public field APIs.
void ATE::validate_field_(int lsb, int width, int pin_count, const char* label) const {
    if (width <= 0) {
        throw std::invalid_argument(std::string(label) + " width must be positive");
    }
    if (lsb < 0 || lsb + width > pin_count) {
        throw std::out_of_range(std::string(label) + " out of range");
    }
}

#ifdef ATE_PYBIND
namespace py = pybind11;

PYBIND11_MODULE(ate, m) {
    m.doc() = "pybind11 wrapper for the Socket-based ATE";
    m.attr("CLOCK_PIN") = py::int_(ATE::kClockPin);
    m.attr("RESET_PIN") = py::int_(ATE::kResetPin);
    m.attr("PIN_IN_COUNT") = py::int_(ATE::kPinInCount);
    m.attr("PIN_OUT_COUNT") = py::int_(ATE::kPinOutCount);

    py::enum_<CompareSpec::Mode>(m, "CompareMode")
        .value("AllPins", CompareSpec::Mode::AllPins)
        .value("SinglePin", CompareSpec::Mode::SinglePin)
        .value("Field", CompareSpec::Mode::Field);

    py::class_<SampleRecord>(m, "SampleRecord")
        .def(py::init<>())
        .def_readonly("cycle", &SampleRecord::cycle)
        .def_readonly("sample_mask", &SampleRecord::sample_mask)
        .def_readonly("raw", &SampleRecord::raw)
        .def_readonly("top_data_snapshot", &SampleRecord::top_data_snapshot)
        .def_readonly("compare_spec", &SampleRecord::compare_spec);

    py::class_<CompareSpec>(m, "CompareSpec")
        .def(py::init<>())
        .def_readwrite("mode", &CompareSpec::mode)
        .def_readwrite("lsb", &CompareSpec::lsb)
        .def_readwrite("width", &CompareSpec::width)
        .def_readwrite("delay", &CompareSpec::delay)
        .def_static("all_pins", &CompareSpec::all_pins, py::arg("delay") = 0)
        .def_static("single_pin", &CompareSpec::single_pin, py::arg("pin"), py::arg("delay") = 0)
        .def_static("field",
                    &CompareSpec::field,
                    py::arg("lsb"),
                    py::arg("width"),
                    py::arg("delay") = 0);

    py::class_<TimingSet>(m, "TimingSet")
        .def(py::init<>())
        .def_readwrite("name", &TimingSet::name)
        .def_readwrite("period_phases", &TimingSet::period_phases)
        .def_readwrite("nrz_rise_phase", &TimingSet::nrz_rise_phase)
        .def_readwrite("rzz_rise_phase", &TimingSet::rzz_rise_phase)
        .def_readwrite("rzz_fall_phase", &TimingSet::rzz_fall_phase)
        .def_readwrite("sample_phase", &TimingSet::sample_phase);

    py::enum_<DriveWaveformKind>(m, "DriveWaveformKind")
        .value("NRZ", DriveWaveformKind::NRZ)
        .value("RZZ", DriveWaveformKind::RZZ);

    py::class_<DriveWaveform>(m, "DriveWaveform")
        .def(py::init<>())
        .def_readwrite("kind", &DriveWaveform::kind)
        .def_readwrite("default_value", &DriveWaveform::default_value)
        .def_static("nrz", &DriveWaveform::nrz, py::arg("default_value") = false)
        .def_static("rzz", &DriveWaveform::rzz, py::arg("default_value") = false);

    py::class_<ATE>(m, "ATE")
        .def(py::init<std::string, bool, uint32_t>(),
             py::arg("wave_name") = "",
             py::arg("trace_enable") = true,
             py::arg("top_data_init") = 0)
        .def("tick", &ATE::tick)
        .def("advance_phase", &ATE::advance_phase)
        .def("advance_period", &ATE::advance_period)
        .def("run_cycles", &ATE::run_cycles, py::arg("cycles"))
        .def("reset", &ATE::reset)
        .def("set_timing", &ATE::set_timing, py::arg("timing"))
        .def("timing", &ATE::timing)
        .def("phase", &ATE::phase)
        .def("phase_in_period", &ATE::phase_in_period)
        .def_static("clock_pin", &ATE::clock_pin)
        .def_static("reset_pin", &ATE::reset_pin)
        .def("bind_rzz_drive",
             [](ATE& self, int pin) { self.bind_rzz_drive(pin); },
             py::arg("pin"))
        .def("bind_rzz_drive",
             [](ATE& self, int pin, DriveWaveform waveform) { self.bind_rzz_drive(pin, waveform); },
             py::arg("pin"),
             py::arg("waveform"))
        .def("clear_rzz_drive", &ATE::clear_rzz_drive, py::arg("pin"))
        .def("clear_rzz_drives", &ATE::clear_rzz_drives)
        .def("clear_input_pin_configs", &ATE::clear_input_pin_configs)
        .def("configure_input_pin",
             &ATE::configure_input_pin,
             py::arg("lsb"),
             py::arg("width"),
             py::arg("waveform"),
             py::arg("default_value") = 0)
        .def("begin_vector_row", &ATE::begin_vector_row)
        .def("activate_input_pin", &ATE::activate_input_pin, py::arg("pin"))
        .def("set_input_field",
             &ATE::set_input_field,
             py::arg("lsb"),
             py::arg("width"),
             py::arg("value"))
        .def("commit_vector_row", &ATE::commit_vector_row)
        .def("clear_output_pin_configs", &ATE::clear_output_pin_configs)
        .def("configure_output_pin",
             &ATE::configure_output_pin,
             py::arg("lsb"),
             py::arg("width"),
             py::arg("default_value") = 0)
        .def("expect_output_field",
             &ATE::expect_output_field,
             py::arg("lsb"),
             py::arg("width"),
             py::arg("expected"))
        .def("top_data", &ATE::top_data)
        .def("set_top_data", &ATE::set_top_data, py::arg("data"))
        .def("clear_drive", &ATE::clear_drive)
        .def("clear_sample", &ATE::clear_sample)
        .def("stage_drive_pin",
             &ATE::stage_drive_pin,
             py::arg("pin"),
             py::arg("value"),
             py::arg("delay") = 0)
        .def("stage_drive_field",
             &ATE::stage_drive_field,
             py::arg("lsb"),
             py::arg("width"),
             py::arg("value"),
             py::arg("delay") = 0)
        .def("stage_drive_pin_wave",
             &ATE::stage_drive_pin_wave,
             py::arg("pin"),
             py::arg("value"),
             py::arg("waveform"),
             py::arg("delay") = 0)
        .def("stage_drive_field_wave",
             &ATE::stage_drive_field_wave,
             py::arg("lsb"),
             py::arg("width"),
             py::arg("value"),
             py::arg("waveform"),
             py::arg("delay") = 0)
        .def("pulse_drive", &ATE::pulse_drive)
        .def("pulse_alert", &ATE::pulse_alert)
        .def("sample", py::overload_cast<>(&ATE::sample))
        .def("sample", py::overload_cast<const CompareSpec&>(&ATE::sample), py::arg("spec"))
        .def("compare_last", &ATE::compare_last)
        .def("compare_all", &ATE::compare_all)
        .def("compare_results", &ATE::compare_results)
        .def("has_compare_results", &ATE::has_compare_results)
        .def("last_compare_result", &ATE::last_compare_result)
        .def("all_compare_results_pass", &ATE::all_compare_results_pass)
        .def("clear_compare_results", &ATE::clear_compare_results)
        .def("print_compare_results", &ATE::print_compare_results)
        .def("print_compare_results_and", &ATE::print_compare_results_and)
        .def("clock", &ATE::clock)
        .def("cycle", &ATE::cycle)
        .def("current_drive_alert_raw", &ATE::current_drive_alert_raw)
        .def("current_drive_counts_raw", &ATE::current_drive_counts_raw)
        .def("current_sample_alert_raw", &ATE::current_sample_alert_raw)
        .def("current_sample_counts_raw", &ATE::current_sample_counts_raw)
        .def("drive_count", &ATE::drive_count, py::arg("pin"))
        .def("sample_count", &ATE::sample_count, py::arg("pin"))
        .def("drive_counts", &ATE::drive_counts)
        .def("sample_counts", &ATE::sample_counts)
        .def("current_output_raw", &ATE::current_output_raw)
        .def("last_sampled_raw", &ATE::last_sampled_raw)
        .def("last_sampled_record", &ATE::last_sampled_record)
        .def("captured_samples", &ATE::captured_samples)
        .def("captured_raw_outputs", &ATE::captured_raw_outputs)
        .def("has_captured_samples", &ATE::has_captured_samples)
        .def("clear_captured_samples", &ATE::clear_captured_samples)
        .def("extract_output_field",
             &ATE::extract_output_field,
             py::arg("raw"),
             py::arg("lsb"),
             py::arg("width"))
        .def("extract_output_bit",
             &ATE::extract_output_bit,
             py::arg("raw"),
             py::arg("bit"))
        .def("extract_counter_field",
             &ATE::extract_counter_field,
             py::arg("raw_counts"),
             py::arg("pin"),
             py::arg("pin_count"))
        .def("print", &ATE::print, py::arg("message"));
}
#endif
