#include "Ate.h"

#include <cstddef>
#include <iostream>
#include <algorithm>
#include <limits>
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

template <typename WideBus>
uint32_t getWideField(const WideBus& bus, int lsb, int width) {
    uint32_t value = 0;
    for (int i = 0; i < width; ++i) {
        bool bit;
        if constexpr (std::is_integral_v<WideBus>) {
            bit = ((bus >> (lsb + i)) & 1U) != 0U;
        } else {
            const std::size_t word = static_cast<std::size_t>((lsb + i) / 32);
            const int offset = (lsb + i) % 32;
            bit = ((bus[word] >> offset) & 1U) != 0U;
        }
        if (bit) {
            value |= 1U << i;
        }
    }
    return value;
}

template <typename Scalar>
void setScalarBit(Scalar& bus, int bit, bool value) {
    const Scalar mask = static_cast<Scalar>(1U << bit);
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
      top_data_(0) {
#ifdef ATE_ENABLE_TRACE
    contextp_->traceEverOn(trace_enable);
#else
    if (trace_enable) {
        throw std::runtime_error("ATE was built without trace support; rebuild with cbuild or pass trace_enable=False");
    }
    contextp_->traceEverOn(false);
#endif
    socketp_ = std::make_unique<VSocket>(contextp_.get(), "TOP");
    set_top_data(top_data_init);

#ifdef ATE_ENABLE_TRACE
    if (trace_enable && !wave_name.empty()) {
        tfp_ = std::make_unique<VerilatedVcdC>();
        socketp_->trace(tfp_.get(), 99);
        tfp_->open(wave_name.c_str());
    }
#endif

    socketp_->ATE_CLK = 0;
    socketp_->ATE_RST_N = 0;
    socketp_->ALERT = 0;
    apply_voltage_configs_();
    clear_driv_();
    clear_samp_();

    init_reset_sequence_();
}

ATE::~ATE() {
#ifdef ATE_ENABLE_TRACE
    if (tfp_) {
        tfp_->close();
    }
#endif
    if (socketp_) {
        socketp_->final();
    }
}

// Internal bootstrap reset used only during construction.
void ATE::init_reset_sequence_() {
    advance_phase();
    advance_phase();

    socketp_->ATE_RST_N = 0;
    for (int i = 0; i < 8; ++i) {
        advance_phase();
    }

    socketp_->ATE_RST_N = 1;
    advance_phase();
    advance_phase();

    clear_captured_samples();
    clear_compare_results();
    pending_compare_specs_.clear();
    nrz_drive_mask_ = 0;
    nrz_drive_values_ = 0;
    nrz_pending_mask_ = 0;
    nrz_pending_values_ = 0;
    nrz_pending_pin_delays_.fill(0);
    nrz_pending_default_flags_.fill(false);
    scheduled_drive_events_.clear();
    scheduled_sample_events_.clear();
    scheduled_alert_events_.clear();
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
    nrz_pending_pin_delays_.fill(0);
    nrz_pending_default_flags_.fill(false);
    scheduled_drive_events_.clear();
    scheduled_sample_events_.clear();
    scheduled_alert_events_.clear();

    advance_phase();
    advance_phase();

    socketp_->ATE_RST_N = 1;
    advance_phase();
    advance_phase();

    clear_captured_samples();
    clear_compare_results();
    pending_compare_specs_.clear();
    nrz_drive_mask_ = 0;
    nrz_drive_values_ = 0;
    nrz_pending_mask_ = 0;
    nrz_pending_values_ = 0;
    nrz_pending_pin_delays_.fill(0);
    nrz_pending_default_flags_.fill(false);
    scheduled_drive_events_.clear();
    scheduled_sample_events_.clear();
    scheduled_alert_events_.clear();
    cycle_ = 0;
    phase_in_period_ = 0;
}

// Compatibility alias: one ATE phase, not one DUT clock period.
void ATE::tick() {
    advance_phase();
}

// Public single-phase advance. This is the base timing primitive for all custom flows.
void ATE::advance_phase() {
    execute_scheduled_drive_events_();
    execute_scheduled_sample_events_();
    execute_scheduled_alert_events_();

    socketp_->ATE_CLK = 0;
    socketp_->eval();
#ifdef ATE_ENABLE_TRACE
    if (tfp_) {
        tfp_->dump(clock_++);
    }
#endif

    socketp_->ATE_CLK = 1;
    socketp_->eval();
    capture_sample_if_ready_();
#ifdef ATE_ENABLE_TRACE
    if (tfp_) {
        tfp_->dump(clock_++);
    }
#endif

    clear_driv_();
    clear_samp_();
    socketp_->ALERT = 0;
    ++phase_;
    phase_in_period_ = (phase_in_period_ + 1U) % timing_.prd;
}

void ATE::advance_to_phase(uint64_t target_phase) {
    if (target_phase < phase_) {
        throw std::invalid_argument("advance_to_phase target is earlier than current phase");
    }
    while (phase_ < target_phase) {
        advance_phase();
    }
}

// Public full timing-period advance. This is the vector-cycle primitive.
void ATE::advance_period() {
    for (uint64_t i = 0; i < timing_.prd; ++i) {
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
    phase_in_period_ %= timing_.prd;
}

void ATE::bind_nrz_drive(int pin, bool value, uint32_t pin_delay) {
    validate_pin_index_(pin, kPinInCount, "NRZ drive pin");

    const uint32_t mask = 1U << pin;
    nrz_pending_mask_ |= mask;
    nrz_pending_pin_delays_[static_cast<std::size_t>(pin)] = pin_delay;
    nrz_pending_default_flags_[static_cast<std::size_t>(pin)] = loading_vector_defaults_;
    if (value) {
        nrz_pending_values_ |= mask;
    } else {
        nrz_pending_values_ &= ~mask;
    }
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

void ATE::load_vector_row_defaults() {
    clear_drive();
    clear_rzz_drives();

    loading_vector_defaults_ = true;
    for (const auto& config : input_pin_configs_) {
        bind_drive_field_wave(config.lsb,
                              config.width,
                              config.default_value,
                              config.waveform);
    }
    loading_vector_defaults_ = false;
}

void ATE::begin_vector_row() {
    load_vector_row_defaults();
}

void ATE::activate_input_pin(int pin, uint32_t pin_delay) {
    const auto& config = input_pin_config_(pin, 1);
    if (config.width != 1) {
        throw std::invalid_argument("activate_input_pin requires a single-bit pin config");
    }
    if (config.waveform.kind == DriveWaveformKind::RZZ) {
        throw std::invalid_argument("activate_input_pin does not support RZZ pins");
    }
    const bool default_value = (config.default_value & 1U) != 0U;
    bind_drive_pin_wave(pin, !default_value, config.waveform, pin_delay);
}

void ATE::set_input_field(int lsb, int width, uint32_t value, uint32_t pin_delay) {
    const auto& config = input_pin_config_(lsb, width);
    if (config.waveform.kind == DriveWaveformKind::RZZ) {
        throw std::invalid_argument("set_input_field does not support RZZ pins");
    }
    if (width < 32 && (value & ~fieldMask(width)) != 0U) {
        throw std::invalid_argument("input field value does not fit field width");
    }
    bind_drive_field_wave(lsb, width, value, config.waveform, pin_delay);
}

void ATE::commit_vector_row() {
    schedule_nrz_pending_drives_();
    schedule_rzz_bound_drives_();
    pulse_drive();
}

void ATE::schedule_input_pin_at(uint64_t due_phase,
                                int pin,
                                bool value,
                                uint32_t pin_delay,
                                uint32_t hold_duration,
                                bool update_nrz_stable,
                                bool default_value_event) {
    validate_pin_index_(pin, kPinInCount, "absolute input pin event");
    schedule_drive_event_(due_phase,
                          pin,
                          value,
                          pin_delay,
                          hold_duration,
                          update_nrz_stable,
                          default_value_event);
}

void ATE::schedule_input_field_at(uint64_t due_phase,
                                  int lsb,
                                  int width,
                                  uint32_t value,
                                  uint32_t pin_delay,
                                  uint32_t hold_duration,
                                  bool update_nrz_stable,
                                  bool default_value_event) {
    validate_field_(lsb, width, kPinInCount, "absolute input field event");
    if (width < 32 && (value & ~fieldMask(width)) != 0U) {
        throw std::invalid_argument("absolute input field value does not fit field width");
    }

    for (int i = 0; i < width; ++i) {
        schedule_input_pin_at(due_phase,
                              lsb + i,
                              ((value >> i) & 1U) != 0U,
                              pin_delay,
                              hold_duration,
                              update_nrz_stable,
                              default_value_event);
    }
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

void ATE::validate_ate_input_voltage_config_(const AteInputVoltageConfig& config) const {
    if (config.vil_uv >= config.vih_uv) {
        throw std::invalid_argument("ATE input voltage config requires VIL < VIH");
    }
}

void ATE::validate_ate_output_voltage_config_(const AteOutputVoltageConfig& config) const {
    if (config.vol_uv > config.voh_uv) {
        throw std::invalid_argument("ATE output voltage config requires VOL <= VOH");
    }
}

void ATE::validate_dut_output_interface_config_(const DutOutputInterfaceConfig& config) const {
    if (config.low_uv >= config.high_uv) {
        throw std::invalid_argument("DUT output interface requires LOW < HIGH");
    }
    if (config.rise_step_uv == 0 || config.fall_step_uv == 0) {
        throw std::invalid_argument("DUT output slew steps must be greater than zero");
    }
}

void ATE::validate_dut_input_interface_config_(const DutInputInterfaceConfig& config) const {
    if (config.rise_step_uv == 0 || config.fall_step_uv == 0) {
        throw std::invalid_argument("DUT input slew steps must be greater than zero");
    }
}

void ATE::configure_ate_input_voltage_pin(int pin, const AteInputVoltageConfig& config) {
    validate_pin_index_(pin, kPinInCount, "ATE input voltage pin");
    validate_ate_input_voltage_config_(config);
    ate_input_voltage_configs_[static_cast<std::size_t>(pin)] = config;
    apply_voltage_configs_();
}

void ATE::configure_ate_input_voltage_field(int lsb,
                                            int width,
                                            const AteInputVoltageConfig& config) {
    validate_field_(lsb, width, kPinInCount, "ATE input voltage field");
    validate_ate_input_voltage_config_(config);
    for (int pin = lsb; pin < lsb + width; ++pin) {
        ate_input_voltage_configs_[static_cast<std::size_t>(pin)] = config;
    }
    apply_voltage_configs_();
}

void ATE::configure_ate_output_voltage_pin(int pin, const AteOutputVoltageConfig& config) {
    validate_pin_index_(pin, kPinOutCount, "ATE output voltage pin");
    validate_ate_output_voltage_config_(config);
    ate_output_voltage_configs_[static_cast<std::size_t>(pin)] = config;
    apply_voltage_configs_();
}

void ATE::configure_ate_output_voltage_field(int lsb,
                                             int width,
                                             const AteOutputVoltageConfig& config) {
    validate_field_(lsb, width, kPinOutCount, "ATE output voltage field");
    validate_ate_output_voltage_config_(config);
    for (int pin = lsb; pin < lsb + width; ++pin) {
        ate_output_voltage_configs_[static_cast<std::size_t>(pin)] = config;
    }
    apply_voltage_configs_();
}

void ATE::configure_dut_input_interface_pin(int pin, const DutInputInterfaceConfig& config) {
    configure_dut_input_interface_field(pin, 1, config);
}

void ATE::configure_dut_input_interface_field(int lsb,
                                              int width,
                                              const DutInputInterfaceConfig& config) {
    validate_field_(lsb, width, kPinInCount, "DUT input interface field");
    validate_dut_input_interface_config_(config);
    for (int pin = lsb; pin < lsb + width; ++pin) {
        dut_input_interface_configs_[static_cast<std::size_t>(pin)] = config;
    }
    apply_voltage_configs_();
}

void ATE::configure_dut_output_interface_pin(int pin, const DutOutputInterfaceConfig& config) {
    configure_dut_output_interface_field(pin, 1, config);
}

void ATE::configure_dut_output_interface_field(int lsb,
                                               int width,
                                               const DutOutputInterfaceConfig& config) {
    validate_field_(lsb, width, kPinOutCount, "DUT output interface field");
    validate_dut_output_interface_config_(config);
    for (int pin = lsb; pin < lsb + width; ++pin) {
        dut_output_interface_configs_[static_cast<std::size_t>(pin)] = config;
    }
    apply_voltage_configs_();
}

void ATE::set_dut_vddq_uv(uint32_t uv) {
    dut_vddq_uv_ = uv;
    apply_voltage_configs_();
}

void ATE::set_analog_mode(bool enabled) {
    analog_mode_ = enabled;
    apply_voltage_configs_();
}

void ATE::set_dut_skew(const DutSkewConfig& config) {
    if (config.rx_dqs > 4 || config.rx_dq > 4 || config.tx_dqs > 4 || config.tx_dq > 4) {
        throw std::invalid_argument("DUT skew values must be in range 0..4");
    }
    dut_skew_ = config;
    apply_voltage_configs_();
}

void ATE::apply_voltage_configs_() {
    socketp_->DUT_ANALOG_ENABLE = analog_mode_ ? 1 : 0;
    socketp_->DUT_VDDQ_UV = dut_vddq_uv_;
    socketp_->DUT_RX_DQS_SKEW = dut_skew_.rx_dqs;
    socketp_->DUT_RX_DQ_SKEW = dut_skew_.rx_dq;
    socketp_->DUT_TX_DQS_SKEW = dut_skew_.tx_dqs;
    socketp_->DUT_TX_DQ_SKEW = dut_skew_.tx_dq;

    clearWideBus(socketp_->ATE_VIL_UV);
    clearWideBus(socketp_->ATE_VIH_UV);
    clearWideBus(socketp_->DUT_VREF_UV);
    clearWideBus(socketp_->DUT_INPUT_RISE_STEP_UV);
    clearWideBus(socketp_->DUT_INPUT_FALL_STEP_UV);
    socketp_->DUT_INPUT_ENABLE = 0;
    for (int pin = 0; pin < kPinInCount; ++pin) {
        const auto& ate_config = ate_input_voltage_configs_[static_cast<std::size_t>(pin)];
        const auto& dut_config = dut_input_interface_configs_[static_cast<std::size_t>(pin)];
        setWideField(socketp_->ATE_VIL_UV, pin * 32, 32, ate_config.vil_uv);
        setWideField(socketp_->ATE_VIH_UV, pin * 32, 32, ate_config.vih_uv);
        setScalarBit(socketp_->DUT_INPUT_ENABLE, pin, dut_config.enabled);
        setWideField(socketp_->DUT_VREF_UV, pin * 32, 32, dut_config.vref_uv);
        setWideField(socketp_->DUT_INPUT_RISE_STEP_UV, pin * 32, 32, dut_config.rise_step_uv);
        setWideField(socketp_->DUT_INPUT_FALL_STEP_UV, pin * 32, 32, dut_config.fall_step_uv);
    }

    clearWideBus(socketp_->DUT_LOW_UV);
    clearWideBus(socketp_->DUT_HIGH_UV);
    clearWideBus(socketp_->DUT_OUTPUT_RISE_STEP_UV);
    clearWideBus(socketp_->DUT_OUTPUT_FALL_STEP_UV);
    clearWideBus(socketp_->ATE_VOL_UV);
    clearWideBus(socketp_->ATE_VOH_UV);
    socketp_->DUT_OUTPUT_ENABLE = 0;
    socketp_->ATE_OUTPUT_ENABLE = 0;
    for (int pin = 0; pin < kPinOutCount; ++pin) {
        const auto& dut_config = dut_output_interface_configs_[static_cast<std::size_t>(pin)];
        const auto& ate_config = ate_output_voltage_configs_[static_cast<std::size_t>(pin)];
        setScalarBit(socketp_->DUT_OUTPUT_ENABLE, pin, dut_config.enabled);
        setWideField(socketp_->DUT_LOW_UV, pin * 32, 32, dut_config.low_uv);
        setWideField(socketp_->DUT_HIGH_UV, pin * 32, 32, dut_config.high_uv);
        setWideField(socketp_->DUT_OUTPUT_RISE_STEP_UV, pin * 32, 32, dut_config.rise_step_uv);
        setWideField(socketp_->DUT_OUTPUT_FALL_STEP_UV, pin * 32, 32, dut_config.fall_step_uv);
        setScalarBit(socketp_->ATE_OUTPUT_ENABLE, pin, analog_mode_ && ate_config.enabled);
        setWideField(socketp_->ATE_VOL_UV, pin * 32, 32, ate_config.vol_uv);
        setWideField(socketp_->ATE_VOH_UV, pin * 32, 32, ate_config.voh_uv);
    }
}

uint32_t ATE::current_input_voltage_uv(int pin) const {
    validate_pin_index_(pin, kPinInCount, "input voltage pin");
    return getWideField(socketp_->PIN_IN_UV, pin * 32, 32);
}

uint32_t ATE::current_ate_input_voltage_uv(int pin) const {
    validate_pin_index_(pin, kPinInCount, "ATE input voltage pin");
    return getWideField(socketp_->ATE_PIN_IN_UV, pin * 32, 32);
}

uint32_t ATE::current_output_voltage_uv(int pin) const {
    validate_pin_index_(pin, kPinOutCount, "output voltage pin");
    return getWideField(socketp_->PIN_OUT_UV, pin * 32, 32);
}

std::vector<uint32_t> ATE::current_input_voltages_uv() const {
    std::vector<uint32_t> values;
    values.reserve(kPinInCount);
    for (int pin = 0; pin < kPinInCount; ++pin) {
        values.push_back(current_input_voltage_uv(pin));
    }
    return values;
}

std::vector<uint32_t> ATE::current_output_voltages_uv() const {
    std::vector<uint32_t> values;
    values.reserve(kPinOutCount);
    for (int pin = 0; pin < kPinOutCount; ++pin) {
        values.push_back(current_output_voltage_uv(pin));
    }
    return values;
}

void ATE::expect_output_field(int lsb, int width, uint32_t expected, uint32_t pin_delay) {
    const auto& config = output_pin_config_(lsb, width);
    if (width < 32 && (expected & ~fieldMask(width)) != 0U) {
        throw std::invalid_argument("output field expected value does not fit field width");
    }
    set_top_data(expected);
    const auto spec = CompareSpec::field(config.lsb, config.width, pin_delay, expected);
    schedule_sample_event_(
        phase_with_offset_(phase_, timing_.stb.edge, timing_.stb.base, "sample"),
        spec);
}

void ATE::schedule_output_field_at(uint64_t due_phase,
                                   int lsb,
                                   int width,
                                   uint32_t expected,
                                   uint32_t pin_delay) {
    const auto& config = output_pin_config_(lsb, width);
    if (width < 32 && (expected & ~fieldMask(width)) != 0U) {
        throw std::invalid_argument("absolute output field expected value does not fit field width");
    }

    set_top_data(expected);
    const auto spec = CompareSpec::field(config.lsb, config.width, pin_delay, expected);
    schedule_sample_event_(due_phase, spec);
}

// Public convenience helper: discard the currently staged drive operation.
void ATE::clear_drive() {
    clear_driv_();
    nrz_pending_mask_ = 0;
    nrz_pending_values_ = 0;
    nrz_pending_pin_delays_.fill(0);
    nrz_pending_default_flags_.fill(false);
}

// Public convenience helper: discard the currently staged sample operation.
void ATE::clear_sample() {
    clear_samp_();
}

void ATE::bind_drive_pin_wave(int pin,
                              bool value,
                              DriveWaveform waveform,
                              uint32_t pin_delay) {
    validate_pin_index_(pin, kPinInCount, "drive pin");

    switch (waveform.kind) {
    case DriveWaveformKind::NRZ:
    case DriveWaveformKind::RZ:
        bind_nrz_drive(pin, value, pin_delay);
        return;
    case DriveWaveformKind::RZZ:
        bind_rzz_drive(pin, DriveWaveform::rzz(value));
        return;
    }
}

void ATE::bind_drive_field_wave(int lsb,
                                int width,
                                uint32_t value,
                                DriveWaveform waveform,
                                uint32_t pin_delay) {
    validate_field_(lsb, width, kPinInCount, "drive field");

    switch (waveform.kind) {
    case DriveWaveformKind::NRZ:
    case DriveWaveformKind::RZ:
    case DriveWaveformKind::RZZ:
        for (int i = 0; i < width; ++i) {
            const bool default_bit = ((value >> i) & 1U) != 0U;
            bind_drive_pin_wave(lsb + i, default_bit, waveform, pin_delay);
        }
        return;
    }
}

void ATE::stage_drive_pin_wave(int pin,
                               bool value,
                               DriveWaveform waveform,
                               uint32_t pin_delay) {
    bind_drive_pin_wave(pin, value, waveform, pin_delay);
}

void ATE::stage_drive_field_wave(int lsb,
                                 int width,
                                 uint32_t value,
                                 DriveWaveform waveform,
                                 uint32_t pin_delay) {
    bind_drive_field_wave(lsb, width, value, waveform, pin_delay);
}

// Public execute step for the staged drive request.
void ATE::pulse_drive() {
    pulse_driv_();
}

void ATE::pulse_alert() {
    socketp_->ALERT = 1;
    advance_phase();
    socketp_->ALERT = 0;
}

void ATE::schedule_alert_at(uint64_t due_phase) {
    schedule_alert_event_(due_phase);
}

void ATE::sample() {
    sample(CompareSpec{});
}

// Run one sample operation through the hardware sampler. Delay belongs here.
void ATE::sample(const CompareSpec& spec) {
    validate_compare_spec_(spec);

    schedule_sample_event_(
        phase_with_offset_(phase_, timing_.stb.edge, timing_.stb.base, "sample"),
        spec);
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
    if (socketp_) {
        socketp_->TOP_DATA = top_data_;
    }
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

// Public raw view of the continuous ATE comparator output. This does not
// create a sample event or append a compare record.
uint32_t ATE::current_output_raw() const {
    return socketp_->PIN_OUT_DIGITAL;
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

void ATE::print_sample_records() const {
    if (captured_samples_.empty()) {
        std::cout << "[samples] empty" << std::endl;
        return;
    }

    std::cout << "[samples] count=" << captured_samples_.size() << std::endl;
    for (std::size_t index = 0; index < captured_samples_.size(); ++index) {
        const auto& sample = captured_samples_[index];
        const uint32_t mask = compare_mask_(sample.compare_spec);
        uint32_t actual = sample.raw & mask;
        uint32_t expected = sample.top_data_snapshot & mask;

        if (sample.compare_spec.mode == CompareSpec::Mode::Field) {
            actual >>= sample.compare_spec.lsb;
            expected >>= sample.compare_spec.lsb;
        } else if (sample.compare_spec.mode == CompareSpec::Mode::SinglePin) {
            actual >>= sample.compare_spec.lsb;
            expected >>= sample.compare_spec.lsb;
        }

        std::cout << "[sample " << index
                  << "] cycle=" << sample.cycle
                  << " actual=0x" << std::hex << actual
                  << " expected=0x" << expected
                  << " raw=0x" << sample.raw
                  << " mask=0x" << mask
                  << " valid=0x" << sample.valid_mask
                  << std::dec
                  << " pass=" << (sample_matches_(sample) ? 1 : 0)
                  << std::endl;
    }
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
    socketp_->DRIV_RETURN_IN = 0;
    clearWideBus(socketp_->DRIV_DELAY);
    clearWideBus(socketp_->DRIV_DURATION);
}

// Internal low-level socket clear. External code should prefer clear_sample().
void ATE::clear_samp_() {
    socketp_->SAMP = 0;
    clearWideBus(socketp_->SAMP_DELAY);
}

// Internal staging helper used by the public drive APIs after validation.
void ATE::set_driv_pin_(int pin,
                        bool value,
                        uint32_t pin_delay,
                        uint32_t hold_duration) {
    uint32_t driv = socketp_->DRIV;
    uint32_t driv_in = socketp_->DRIV_IN;
    uint32_t driv_return_in = socketp_->DRIV_RETURN_IN;

    setScalarBit(driv, pin, true);
    setScalarBit(driv_in, pin, value);
    setScalarBit(driv_return_in, pin, input_pin_default_value_(pin));

    socketp_->DRIV = driv;
    socketp_->DRIV_IN = driv_in;
    socketp_->DRIV_RETURN_IN = driv_return_in;
    setWideField(socketp_->DRIV_DELAY,
                 pin * kDelayWidth,
                 kDelayWidth,
                 pin_delay);
    setWideField(socketp_->DRIV_DURATION,
                 pin * kDelayWidth,
                 kDelayWidth,
                 hold_duration);
}

// Internal staging helper used by the public drive APIs after validation.
void ATE::set_driv_field_(int lsb, int width, uint32_t value, uint32_t pin_delay, uint32_t hold_duration) {
    for (int i = 0; i < width; ++i) {
        set_driv_pin_(lsb + i, ((value >> i) & 1U) != 0U, pin_delay, hold_duration);
    }
}

// Internal staging helper used by the public sample APIs after validation.
void ATE::set_samp_pin_(int pin, uint32_t pin_delay) {
    socketp_->SAMP |= (1U << pin);
    setWideField(socketp_->SAMP_DELAY,
                 pin * kDelayWidth,
                 kDelayWidth,
                 pin_delay);
}

// Internal staging helper used by the public sample APIs after validation.
void ATE::set_samp_field_(int lsb, int width, uint32_t pin_delay) {
    for (int i = 0; i < width; ++i) {
        set_samp_pin_(lsb + i, pin_delay);
    }
}

// Internal helper for stage_sample_all().
void ATE::enable_all_samples_(uint32_t pin_delay) {
    for (int pin = 0; pin < kPinOutCount; ++pin) {
        set_samp_pin_(pin, pin_delay);
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

void ATE::schedule_drive_event_(uint64_t due_phase,
                                int pin,
                                bool value,
                                uint32_t pin_delay,
                                uint32_t hold_duration,
                                bool update_nrz_stable,
                                bool default_value_event) {
    ScheduledDriveEvent event{
        .due_phase = due_phase,
        .pin = pin,
        .value = value,
        .pin_delay = pin_delay,
        .hold_duration = hold_duration,
        .update_nrz_stable = update_nrz_stable,
        .default_value_event = default_value_event,
    };
    auto insert_at = scheduled_drive_events_.begin();
    while (insert_at != scheduled_drive_events_.end()) {
        if (insert_at->due_phase > event.due_phase) {
            break;
        }
        if (insert_at->due_phase == event.due_phase &&
            insert_at->default_value_event &&
            !event.default_value_event) {
            ++insert_at;
            continue;
        }
        if (insert_at->due_phase == event.due_phase &&
            !insert_at->default_value_event &&
            event.default_value_event) {
            break;
        }
        ++insert_at;
    }
    scheduled_drive_events_.insert(insert_at, event);
}

void ATE::schedule_nrz_pending_drives_() {
    uint32_t updated_mask = 0;
    if (nrz_pending_mask_ != 0U) {
        updated_mask = nrz_pending_mask_;
        const uint64_t nrz_phase =
            phase_in_period_ <= timing_.nrz.edge
                ? timing_.nrz.edge - phase_in_period_
                : 0U;
        const uint64_t due_phase =
            phase_with_offset_(phase_, nrz_phase, timing_.nrz.base, "nrz");

        for (int pin = 0; pin < kPinInCount; ++pin) {
            const uint32_t mask = 1U << pin;
            if ((updated_mask & mask) == 0U) {
                continue;
            }
            const bool value = (nrz_pending_values_ & mask) != 0U;
            const uint32_t pin_delay = nrz_pending_pin_delays_[static_cast<std::size_t>(pin)];
            const bool default_value_event =
                nrz_pending_default_flags_[static_cast<std::size_t>(pin)];
            const bool already_stable =
                pin_delay == 0U &&
                !has_scheduled_nrz_stable_event_(pin) &&
                (nrz_drive_mask_ & mask) != 0U &&
                ((nrz_drive_values_ & mask) != 0U) == value;
            if (already_stable) {
                nrz_pending_pin_delays_[static_cast<std::size_t>(pin)] = 0;
                continue;
            }
            schedule_drive_event_(due_phase,
                                  pin,
                                  value,
                                  pin_delay,
                                  pin_delay == 0U ? 0U : timing_.prd,
                                  pin_delay == 0U,
                                  default_value_event);
            nrz_pending_pin_delays_[static_cast<std::size_t>(pin)] = 0;
            nrz_pending_default_flags_[static_cast<std::size_t>(pin)] = false;
        }

        nrz_pending_mask_ = 0;
        nrz_pending_values_ = 0;
        nrz_pending_default_flags_.fill(false);
    }

}

void ATE::schedule_rzz_bound_drives_() {
    const uint64_t row_start_phase = phase_;
    for (int pin = 0; pin < kPinInCount; ++pin) {
        const uint32_t mask = 1U << pin;
        if ((rzz_drive_mask_ & mask) == 0U) {
            continue;
        }
        const bool default_value = (rzz_default_values_ & mask) != 0U;
        schedule_drive_event_(phase_with_offset_(row_start_phase,
                                                 timing_.rzz.edge_1,
                                                 timing_.rzz.base,
                                                 "rzz_rise"),
                              pin,
                              !default_value);
        schedule_drive_event_(phase_with_offset_(row_start_phase,
                                                 timing_.rzz.edge_2,
                                                 timing_.rzz.base,
                                                 "rzz_fall"),
                              pin,
                              default_value);
    }
}

void ATE::execute_scheduled_drive_events_() {
    while (!scheduled_drive_events_.empty() &&
           scheduled_drive_events_.front().due_phase <= phase_) {
        const auto event = scheduled_drive_events_.front();
        scheduled_drive_events_.pop_front();

        const uint32_t mask = 1U << event.pin;
        set_driv_pin_(event.pin,
                      event.value,
                      event.pin_delay,
                      event.hold_duration);
        if (event.update_nrz_stable) {
            nrz_drive_mask_ |= mask;
            if (event.value) {
                nrz_drive_values_ |= mask;
            } else {
                nrz_drive_values_ &= ~mask;
            }
        }
    }
}

bool ATE::has_scheduled_nrz_stable_event_(int pin) const {
    for (const auto& event : scheduled_drive_events_) {
        if (event.pin == pin && event.update_nrz_stable) {
            return true;
        }
    }
    return false;
}

void ATE::schedule_sample_event_(uint64_t due_phase, const CompareSpec& spec) {
    validate_compare_spec_(spec);
    ScheduledSampleEvent event{
        .due_phase = due_phase,
        .spec = spec,
    };
    const auto insert_at = std::upper_bound(
        scheduled_sample_events_.begin(),
        scheduled_sample_events_.end(),
        due_phase,
        [](uint64_t due, const ScheduledSampleEvent& queued) {
            return due < queued.due_phase;
        });
    scheduled_sample_events_.insert(insert_at, event);
}

void ATE::execute_scheduled_sample_events_() {
    while (!scheduled_sample_events_.empty() &&
           scheduled_sample_events_.front().due_phase <= phase_) {
        const auto event = scheduled_sample_events_.front();
        scheduled_sample_events_.pop_front();

        pending_compare_specs_.push_back(PendingCompareSpec{
            .group = event.due_phase,
            .spec = event.spec,
        });
        switch (event.spec.mode) {
        case CompareSpec::Mode::AllPins:
            enable_all_samples_(event.spec.pin_delay);
            break;
        case CompareSpec::Mode::SinglePin:
            set_samp_pin_(event.spec.lsb, event.spec.pin_delay);
            break;
        case CompareSpec::Mode::Field:
            set_samp_field_(event.spec.lsb, event.spec.width, event.spec.pin_delay);
            break;
        }
    }
}

void ATE::schedule_alert_event_(uint64_t due_phase) {
    const auto insert_at = std::upper_bound(
        scheduled_alert_events_.begin(),
        scheduled_alert_events_.end(),
        due_phase);
    scheduled_alert_events_.insert(insert_at, due_phase);
}

void ATE::execute_scheduled_alert_events_() {
    while (!scheduled_alert_events_.empty() &&
           scheduled_alert_events_.front() <= phase_) {
        scheduled_alert_events_.pop_front();
        socketp_->ALERT = 1;
    }
}

uint64_t ATE::phase_with_offset_(uint64_t row_start_phase,
                                 uint64_t waveform_phase,
                                 int64_t base_phase,
                                 const char* label) const {
    uint64_t offset = waveform_phase;
    if (base_phase < 0) {
        const uint64_t magnitude = static_cast<uint64_t>(-(base_phase + 1)) + 1U;
        if (magnitude > offset) {
            throw std::out_of_range(std::string("timing ") + label + " offset is before row start");
        }
        offset -= magnitude;
    } else {
        const uint64_t magnitude = static_cast<uint64_t>(base_phase);
        if (magnitude > std::numeric_limits<uint64_t>::max() - offset) {
            throw std::out_of_range(std::string("timing ") + label + " offset overflows");
        }
        offset += magnitude;
    }
    if (offset > std::numeric_limits<uint64_t>::max() - row_start_phase) {
        throw std::out_of_range(std::string("timing ") + label + " phase overflows");
    }
    if (row_start_phase + offset < row_start_phase) {
        throw std::out_of_range(std::string("timing ") + label + " offset is before row start");
    }
    return row_start_phase + offset;
}

const InputPinConfig& ATE::input_pin_config_(int lsb, int width) const {
    for (const auto& config : input_pin_configs_) {
        if (config.lsb == lsb && config.width == width) {
            return config;
        }
    }
    throw std::invalid_argument("input pin config not found");
}

bool ATE::input_pin_default_value_(int pin) const {
    for (const auto& config : input_pin_configs_) {
        if (pin >= config.lsb && pin < config.lsb + config.width) {
            const int field_bit = pin - config.lsb;
            return ((config.default_value >> field_bit) & 1U) != 0U;
        }
    }
    throw std::invalid_argument("input pin default config not found");
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

    bool captured_any = false;
    // Bug note:
    // - HandshakeEcho CHECK samples several output pins at the same STB phase;
    //   those compare specs must be allowed to consume one shared SAMP_ALERT.
    // - MRR3/serial reads schedule one sample per row with hardware delay; by
    //   the first delayed alert arrives, later rows may already be pending, but
    //   they must not be consumed until their own delayed alert.
    // The scheduled due phase is therefore the capture group boundary.
    const uint64_t captured_group = pending_compare_specs_.empty()
        ? 0
        : pending_compare_specs_.front().group;
    while (!pending_compare_specs_.empty()) {
        const auto pending = pending_compare_specs_.front();
        if (pending.group != captured_group) {
            break;
        }
        const auto captured_spec = pending.spec;
        const uint32_t requested_mask = compare_mask_(captured_spec);
        if ((socketp_->SAMP_ALERT & requested_mask) != requested_mask) {
            break;
        }

        pending_compare_specs_.pop_front();
        last_sample_.cycle = cycle_;
        last_sample_.sample_mask = socketp_->SAMP_ALERT;
        last_sample_.raw = socketp_->SAMP_OUT;
        last_sample_.valid_mask = socketp_->SAMP_VALID;
        last_sample_.top_data_snapshot = aligned_compare_value_(captured_spec);
        last_sample_.compare_spec = captured_spec;
        captured_samples_.push_back(last_sample_);
        captured_any = true;
    }

    if (!captured_any) {
        last_sample_.cycle = cycle_;
        last_sample_.sample_mask = socketp_->SAMP_ALERT;
        last_sample_.raw = socketp_->SAMP_OUT;
        last_sample_.valid_mask = socketp_->SAMP_VALID;
        last_sample_.top_data_snapshot = 0;
        last_sample_.compare_spec = CompareSpec{};
        captured_samples_.push_back(last_sample_);
    }
}

// Build the bit-mask that a compare request requires the sample to cover.
uint32_t ATE::aligned_compare_value_(const CompareSpec& spec) const {
    switch (spec.mode) {
    case CompareSpec::Mode::AllPins:
        return spec.expected & kCompareMask;
    case CompareSpec::Mode::SinglePin:
        return ((spec.expected & 1U) << spec.lsb) & kCompareMask;
    case CompareSpec::Mode::Field:
        return ((spec.expected & fieldMask(spec.width)) << spec.lsb) & kCompareMask;
    }

    return spec.expected & kCompareMask;
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
    if ((sample.valid_mask & requested_mask) != requested_mask) {
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
        .def_readonly("valid_mask", &SampleRecord::valid_mask)
        .def_readonly("top_data_snapshot", &SampleRecord::top_data_snapshot)
        .def_readonly("compare_spec", &SampleRecord::compare_spec);

    py::class_<CompareSpec>(m, "CompareSpec")
        .def(py::init<>())
        .def_readwrite("mode", &CompareSpec::mode)
        .def_readwrite("lsb", &CompareSpec::lsb)
        .def_readwrite("width", &CompareSpec::width)
        .def_readwrite("pin_delay", &CompareSpec::pin_delay)
        .def_property("delay",
                      [](const CompareSpec& spec) { return spec.pin_delay; },
                      [](CompareSpec& spec, uint32_t value) { spec.pin_delay = value; })
        .def_readwrite("expected", &CompareSpec::expected)
        .def_static("all_pins",
                    &CompareSpec::all_pins,
                    py::arg("pin_delay") = 0,
                    py::arg("expected") = 0)
        .def_static("single_pin",
                    &CompareSpec::single_pin,
                    py::arg("pin"),
                    py::arg("pin_delay") = 0,
                    py::arg("expected") = 0)
        .def_static("field",
                    &CompareSpec::field,
                    py::arg("lsb"),
                    py::arg("width"),
                    py::arg("pin_delay") = 0,
                    py::arg("expected") = 0);

    py::class_<SingleEdgeTiming>(m, "SingleEdgeTiming")
        .def(py::init<>())
        .def_readwrite("edge", &SingleEdgeTiming::edge)
        .def_readwrite("base", &SingleEdgeTiming::base);

    py::class_<TwoEdgeTiming>(m, "TwoEdgeTiming")
        .def(py::init<>())
        .def_readwrite("edge_1", &TwoEdgeTiming::edge_1)
        .def_readwrite("edge_2", &TwoEdgeTiming::edge_2)
        .def_readwrite("base", &TwoEdgeTiming::base);

    py::class_<TimingSet>(m, "TimingSet")
        .def(py::init<>())
        .def_readwrite("name", &TimingSet::name)
        .def_readwrite("prd", &TimingSet::prd)
        .def_readwrite("nrz", &TimingSet::nrz)
        .def_readwrite("rz", &TimingSet::rz)
        .def_readwrite("rzz", &TimingSet::rzz)
        .def_readwrite("stb", &TimingSet::stb);

    py::class_<AteInputVoltageConfig>(m, "AteInputVoltageConfig")
        .def(py::init<>())
        .def_readwrite("vil_uv", &AteInputVoltageConfig::vil_uv)
        .def_readwrite("vih_uv", &AteInputVoltageConfig::vih_uv);

    py::class_<AteOutputVoltageConfig>(m, "AteOutputVoltageConfig")
        .def(py::init<>())
        .def_readwrite("enabled", &AteOutputVoltageConfig::enabled)
        .def_readwrite("vol_uv", &AteOutputVoltageConfig::vol_uv)
        .def_readwrite("voh_uv", &AteOutputVoltageConfig::voh_uv);

    py::class_<DutInputInterfaceConfig>(m, "DutInputInterfaceConfig")
        .def(py::init<>())
        .def_readwrite("enabled", &DutInputInterfaceConfig::enabled)
        .def_readwrite("vref_uv", &DutInputInterfaceConfig::vref_uv)
        .def_readwrite("rise_step_uv", &DutInputInterfaceConfig::rise_step_uv)
        .def_readwrite("fall_step_uv", &DutInputInterfaceConfig::fall_step_uv);

    py::class_<DutOutputInterfaceConfig>(m, "DutOutputInterfaceConfig")
        .def(py::init<>())
        .def_readwrite("enabled", &DutOutputInterfaceConfig::enabled)
        .def_readwrite("low_uv", &DutOutputInterfaceConfig::low_uv)
        .def_readwrite("high_uv", &DutOutputInterfaceConfig::high_uv)
        .def_readwrite("rise_step_uv", &DutOutputInterfaceConfig::rise_step_uv)
        .def_readwrite("fall_step_uv", &DutOutputInterfaceConfig::fall_step_uv);

    py::enum_<DriveWaveformKind>(m, "DriveWaveformKind")
        .value("NRZ", DriveWaveformKind::NRZ)
        .value("RZ", DriveWaveformKind::RZ)
        .value("RZZ", DriveWaveformKind::RZZ);

    py::class_<DriveWaveform>(m, "DriveWaveform")
        .def(py::init<>())
        .def_readwrite("kind", &DriveWaveform::kind)
        .def_readwrite("default_value", &DriveWaveform::default_value)
        .def_static("nrz", &DriveWaveform::nrz, py::arg("default_value") = false)
        .def_static("rz", &DriveWaveform::rz, py::arg("default_value") = false)
        .def_static("rzz", &DriveWaveform::rzz, py::arg("default_value") = false);

    py::class_<ATE>(m, "ATE")
        .def(py::init<std::string, bool, uint32_t>(),
             py::arg("wave_name") = "",
             py::arg("trace_enable") = true,
             py::arg("top_data_init") = 0)
        .def("tick", &ATE::tick)
        .def("advance_phase", &ATE::advance_phase)
        .def("advance_to_phase", &ATE::advance_to_phase, py::arg("target_phase"))
        .def("advance_period", &ATE::advance_period)
        .def("run_cycles", &ATE::run_cycles, py::arg("cycles"))
        .def("reset", &ATE::reset)
        .def("set_timing", &ATE::set_timing, py::arg("timing"))
        .def("timing", &ATE::timing)
        .def("phase", &ATE::phase)
        .def("phase_in_period", &ATE::phase_in_period)
        .def("bind_drive_pin_wave",
             &ATE::bind_drive_pin_wave,
             py::arg("pin"),
             py::arg("value"),
             py::arg("waveform"),
             py::arg("pin_delay") = 0)
        .def("bind_drive_field_wave",
             &ATE::bind_drive_field_wave,
             py::arg("lsb"),
             py::arg("width"),
             py::arg("value"),
             py::arg("waveform"),
             py::arg("pin_delay") = 0)
        .def("bind_nrz_drive",
             &ATE::bind_nrz_drive,
             py::arg("pin"),
             py::arg("value"),
             py::arg("pin_delay") = 0)
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
        .def("load_vector_row_defaults", &ATE::load_vector_row_defaults)
        .def("begin_vector_row", &ATE::begin_vector_row)
        .def("activate_input_pin", &ATE::activate_input_pin, py::arg("pin"), py::arg("pin_delay") = 0)
        .def("set_input_field",
             &ATE::set_input_field,
             py::arg("lsb"),
             py::arg("width"),
             py::arg("value"),
             py::arg("pin_delay") = 0)
        .def("commit_vector_row", &ATE::commit_vector_row)
        .def("schedule_input_pin_at",
             &ATE::schedule_input_pin_at,
             py::arg("due_phase"),
             py::arg("pin"),
             py::arg("value"),
             py::arg("pin_delay") = 0,
             py::arg("hold_duration") = 0,
             py::arg("update_nrz_stable") = false,
             py::arg("default_value_event") = false)
        .def("schedule_input_field_at",
             &ATE::schedule_input_field_at,
             py::arg("due_phase"),
             py::arg("lsb"),
             py::arg("width"),
             py::arg("value"),
             py::arg("pin_delay") = 0,
             py::arg("hold_duration") = 0,
             py::arg("update_nrz_stable") = false,
             py::arg("default_value_event") = false)
        .def("clear_output_pin_configs", &ATE::clear_output_pin_configs)
        .def("configure_output_pin",
             &ATE::configure_output_pin,
             py::arg("lsb"),
             py::arg("width"),
             py::arg("default_value") = 0)
        .def("configure_ate_input_voltage_pin",
             &ATE::configure_ate_input_voltage_pin,
             py::arg("pin"),
             py::arg("config"))
        .def("configure_ate_input_voltage_field",
             &ATE::configure_ate_input_voltage_field,
             py::arg("lsb"),
             py::arg("width"),
             py::arg("config"))
        .def("configure_ate_output_voltage_pin",
             &ATE::configure_ate_output_voltage_pin,
             py::arg("pin"),
             py::arg("config"))
        .def("configure_ate_output_voltage_field",
             &ATE::configure_ate_output_voltage_field,
             py::arg("lsb"),
             py::arg("width"),
             py::arg("config"))
        .def("set_analog_mode", &ATE::set_analog_mode, py::arg("enabled"))
        .def("analog_mode", &ATE::analog_mode)
        .def("configure_dut_input_interface_pin",
             &ATE::configure_dut_input_interface_pin,
             py::arg("pin"),
             py::arg("config"))
        .def("configure_dut_input_interface_field",
             &ATE::configure_dut_input_interface_field,
             py::arg("lsb"),
             py::arg("width"),
             py::arg("config"))
        .def("configure_dut_output_interface_pin",
             &ATE::configure_dut_output_interface_pin,
             py::arg("pin"),
             py::arg("config"))
        .def("configure_dut_output_interface_field",
             &ATE::configure_dut_output_interface_field,
             py::arg("lsb"),
             py::arg("width"),
             py::arg("config"))
        .def("expect_output_field",
             &ATE::expect_output_field,
             py::arg("lsb"),
             py::arg("width"),
             py::arg("expected"),
             py::arg("pin_delay") = 0)
        .def("schedule_output_field_at",
             &ATE::schedule_output_field_at,
             py::arg("due_phase"),
             py::arg("lsb"),
             py::arg("width"),
             py::arg("expected"),
             py::arg("pin_delay") = 0)
        .def("set_dut_vddq_uv", &ATE::set_dut_vddq_uv, py::arg("uv"))
        .def("set_dut_vdd_uv", &ATE::set_dut_vdd_uv, py::arg("uv"))
        .def("dut_vddq_uv", &ATE::dut_vddq_uv)
        .def("dut_vdd_uv", &ATE::dut_vdd_uv)
        .def("current_input_voltage_uv", &ATE::current_input_voltage_uv, py::arg("pin"))
        .def("current_ate_input_voltage_uv", &ATE::current_ate_input_voltage_uv, py::arg("pin"))
        .def("current_output_voltage_uv", &ATE::current_output_voltage_uv, py::arg("pin"))
        .def("current_input_voltages_uv", &ATE::current_input_voltages_uv)
        .def("current_output_voltages_uv", &ATE::current_output_voltages_uv)
        .def("top_data", &ATE::top_data)
        .def("set_top_data", &ATE::set_top_data, py::arg("data"))
        .def("clear_drive", &ATE::clear_drive)
        .def("clear_sample", &ATE::clear_sample)
        .def("stage_drive_pin_wave",
             &ATE::stage_drive_pin_wave,
             py::arg("pin"),
             py::arg("value"),
             py::arg("waveform"),
             py::arg("pin_delay") = 0)
        .def("stage_drive_field_wave",
             &ATE::stage_drive_field_wave,
             py::arg("lsb"),
             py::arg("width"),
             py::arg("value"),
             py::arg("waveform"),
             py::arg("pin_delay") = 0)
        .def("pulse_drive", &ATE::pulse_drive)
        .def("pulse_alert", &ATE::pulse_alert)
        .def("schedule_alert_at", &ATE::schedule_alert_at, py::arg("due_phase"))
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
        .def("sample_records", &ATE::captured_samples)
        .def("print_sample_records", &ATE::print_sample_records)
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
