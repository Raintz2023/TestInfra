#include "AteBench.h"

#include <algorithm>
#include <limits>
#include <stdexcept>
#include <type_traits>
#include <unordered_set>
#include <utility>

namespace {

uint32_t value_mask(int width) {
    return width >= 32 ? 0xffffffffU : (1U << width) - 1U;
}

bool overlaps(int lhs_lsb, int lhs_width, int rhs_lsb, int rhs_width) {
    return lhs_lsb < rhs_lsb + rhs_width && rhs_lsb < lhs_lsb + lhs_width;
}

}  // namespace

VectorRow& VectorRow::drive(std::string pin_name, uint32_t value, uint32_t pin_delay) {
    actions_.push_back(Action{ActionKind::Drive, std::move(pin_name), value, pin_delay});
    return *this;
}

VectorRow& VectorRow::pulse(std::string pin_name, uint32_t pin_delay) {
    actions_.push_back(Action{ActionKind::Pulse, std::move(pin_name), 0, pin_delay});
    return *this;
}

VectorRow& VectorRow::sample(std::string pin_name, uint32_t expected, uint32_t pin_delay) {
    actions_.push_back(Action{ActionKind::Sample, std::move(pin_name), expected, pin_delay});
    return *this;
}

VectorRow& VectorRow::alert() {
    actions_.push_back(Action{ActionKind::Alert, {}, 0, 0});
    return *this;
}

AteEvent::AteEvent(std::string name)
    : name_(std::move(name)) {}

AteEvent& AteEvent::run(VectorRow row) {
    steps_.emplace_back(std::in_place_type<RunStep>, std::move(row));
    return *this;
}

AteEvent& AteEvent::idle(uint32_t rows) {
    steps_.emplace_back(std::in_place_type<IdleStep>, rows);
    return *this;
}

AteEvent& AteEvent::advance_phases(uint64_t phases) {
    steps_.emplace_back(std::in_place_type<AdvanceStep>, phases);
    return *this;
}

void AteEvent::execute(AteBench& bench) const {
    for (const auto& step : steps_) {
        std::visit([&](const auto& item) {
            using Step = std::decay_t<decltype(item)>;
            if constexpr (std::is_same_v<Step, RunStep>) {
                bench.run(item.row);
            } else if constexpr (std::is_same_v<Step, IdleStep>) {
                bench.idle(item.rows);
            } else if constexpr (std::is_same_v<Step, AdvanceStep>) {
                bench.advance_phases(item.phases);
            }
        }, step);
    }
}

AteBench::AteBench(AteBenchConfig config)
    : config_(std::move(config)),
      ate_(config_.wave_path, config_.trace_enable) {
    validate_config_();
    for (std::size_t i = 0; i < config_.inputs.size(); ++i) {
        input_by_name_.emplace(config_.inputs[i].name, i);
    }
    for (std::size_t i = 0; i < config_.outputs.size(); ++i) {
        output_by_name_.emplace(config_.outputs[i].name, i);
    }
    configure_engine_();
}

void AteBench::validate_config_() const {
    validate_timing_set(config_.timing);
    std::unordered_set<std::string> names;

    for (std::size_t i = 0; i < config_.inputs.size(); ++i) {
        const auto& pin = config_.inputs[i];
        if (pin.name.empty()) {
            throw std::invalid_argument("input pin name cannot be empty");
        }
        if (!names.insert(pin.name).second) {
            throw std::invalid_argument("duplicate pin name: " + pin.name);
        }
        if (pin.lsb < 0 || pin.width <= 0 || pin.lsb + pin.width > ATE::kPinInCount) {
            throw std::out_of_range("input pin range is invalid: " + pin.name);
        }
        if ((pin.default_value & ~value_mask(pin.width)) != 0U) {
            throw std::invalid_argument("input default value overflows pin width: " + pin.name);
        }
        for (std::size_t j = 0; j < i; ++j) {
            const auto& other = config_.inputs[j];
            if (overlaps(pin.lsb, pin.width, other.lsb, other.width)) {
                throw std::invalid_argument("input pin ranges overlap: " + other.name + " and " + pin.name);
            }
        }
    }

    for (std::size_t i = 0; i < config_.outputs.size(); ++i) {
        const auto& pin = config_.outputs[i];
        if (pin.name.empty()) {
            throw std::invalid_argument("output pin name cannot be empty");
        }
        if (!names.insert(pin.name).second) {
            throw std::invalid_argument("duplicate pin name: " + pin.name);
        }
        if (pin.lsb < 0 || pin.width <= 0 || pin.lsb + pin.width > ATE::kPinOutCount) {
            throw std::out_of_range("output pin range is invalid: " + pin.name);
        }
        for (std::size_t j = 0; j < i; ++j) {
            const auto& other = config_.outputs[j];
            if (overlaps(pin.lsb, pin.width, other.lsb, other.width)) {
                throw std::invalid_argument("output pin ranges overlap: " + other.name + " and " + pin.name);
            }
        }
    }

    std::unordered_set<std::string> dut_input_names;
    for (const auto& interface : config_.dut_interface.inputs) {
        if (!dut_input_names.insert(interface.pin_name).second) {
            throw std::invalid_argument("duplicate DUT input interface: " + interface.pin_name);
        }
        const auto pin = std::find_if(config_.inputs.begin(), config_.inputs.end(),
            [&](const InputPinDef& item) { return item.name == interface.pin_name; });
        if (pin == config_.inputs.end()) {
            throw std::invalid_argument("DUT input interface references unknown input pin: " + interface.pin_name);
        }
    }

    std::unordered_set<std::string> dut_output_names;
    for (const auto& interface : config_.dut_interface.outputs) {
        if (!dut_output_names.insert(interface.pin_name).second) {
            throw std::invalid_argument("duplicate DUT output interface: " + interface.pin_name);
        }
        const auto pin = std::find_if(config_.outputs.begin(), config_.outputs.end(),
            [&](const OutputPinDef& item) { return item.name == interface.pin_name; });
        if (pin == config_.outputs.end()) {
            throw std::invalid_argument("DUT output interface references unknown output pin: " + interface.pin_name);
        }
    }

    for (const auto& [name, uv] : config_.power_uv) {
        (void)uv;
        if (name != "VDDQ" && name != "VDD") {
            throw std::invalid_argument("unknown POWER rail: " + name);
        }
    }
}

void AteBench::configure_engine_() {
    ate_.set_timing(config_.timing);
    const bool analog_mode =
        std::any_of(config_.inputs.begin(), config_.inputs.end(),
                    [](const InputPinDef& pin) { return pin.ate_voltage.has_value(); }) ||
        std::any_of(config_.outputs.begin(), config_.outputs.end(),
                    [](const OutputPinDef& pin) { return pin.ate_voltage.has_value(); }) ||
        !config_.dut_interface.inputs.empty() || !config_.dut_interface.outputs.empty();
    ate_.set_analog_mode(analog_mode);
    const auto vddq = config_.power_uv.find("VDDQ");
    const auto legacy_vdd = config_.power_uv.find("VDD");
    if (vddq != config_.power_uv.end()) {
        ate_.set_dut_vddq_uv(vddq->second);
    } else if (legacy_vdd != config_.power_uv.end()) {
        ate_.set_dut_vddq_uv(legacy_vdd->second);
    } else {
        ate_.set_dut_vddq_uv(1'200'000);
    }
    ate_.set_dut_skew(config_.skew);

    ate_.clear_input_pin_configs();
    for (const auto& pin : config_.inputs) {
        ate_.configure_input_pin(pin.lsb, pin.width, pin.waveform, pin.default_value);
        if (pin.ate_voltage) {
            ate_.configure_ate_input_voltage_field(pin.lsb, pin.width, *pin.ate_voltage);
        }
    }

    ate_.clear_output_pin_configs();
    for (const auto& pin : config_.outputs) {
        ate_.configure_output_pin(pin.lsb, pin.width);
        if (pin.ate_voltage) {
            ate_.configure_ate_output_voltage_field(pin.lsb, pin.width, *pin.ate_voltage);
        }
    }

    for (const auto& interface : config_.dut_interface.inputs) {
        const auto& pin = input_pin_(interface.pin_name);
        ate_.configure_dut_input_interface_field(pin.lsb, pin.width, interface.config);
    }
    for (const auto& interface : config_.dut_interface.outputs) {
        const auto& pin = output_pin_(interface.pin_name);
        ate_.configure_dut_output_interface_field(pin.lsb, pin.width, interface.config);
    }
}

const InputPinDef& AteBench::input_pin_(const std::string& name) const {
    const auto found = input_by_name_.find(name);
    if (found == input_by_name_.end()) {
        if (output_by_name_.contains(name)) {
            throw std::invalid_argument("pin is output-only: " + name);
        }
        throw std::invalid_argument("unknown input pin: " + name);
    }
    return config_.inputs[found->second];
}

const OutputPinDef& AteBench::output_pin_(const std::string& name) const {
    const auto found = output_by_name_.find(name);
    if (found == output_by_name_.end()) {
        if (input_by_name_.contains(name)) {
            throw std::invalid_argument("pin is input-only: " + name);
        }
        throw std::invalid_argument("unknown output pin: " + name);
    }
    return config_.outputs[found->second];
}

uint64_t AteBench::row_phase_(uint64_t row_start,
                              uint64_t edge,
                              int64_t base,
                              const char* label) const {
    uint64_t offset = edge;
    if (base < 0) {
        const uint64_t magnitude = static_cast<uint64_t>(-(base + 1)) + 1U;
        if (magnitude > offset) {
            throw std::out_of_range(std::string(label) + " phase is outside the schedulable timeline");
        }
        offset -= magnitude;
    } else if (static_cast<uint64_t>(base) > std::numeric_limits<uint64_t>::max() - offset) {
        throw std::out_of_range(std::string(label) + " phase is outside the schedulable timeline");
    } else {
        offset += static_cast<uint64_t>(base);
    }
    if (offset > std::numeric_limits<uint64_t>::max() - row_start) {
        throw std::out_of_range(std::string(label) + " phase is outside the schedulable timeline");
    }
    return row_start + offset;
}

void AteBench::run(const VectorRow& row) {
    const uint64_t row_start = ate_.phase();
    uint32_t driven_mask = 0;
    uint32_t sampled_mask = 0;

    // Validate the complete row before staging anything into ATE. A rejected
    // row therefore cannot leave half of its actions in the scheduler.
    for (const auto& action : row.actions_) {
        switch (action.kind) {
        case VectorRow::ActionKind::Drive: {
            const auto& pin = input_pin_(action.pin_name);
            const uint32_t mask = value_mask(pin.width) << pin.lsb;
            if ((driven_mask & mask) != 0U) {
                throw std::invalid_argument("input pin driven more than once in one row: " + pin.name);
            }
            if ((action.value & ~value_mask(pin.width)) != 0U) {
                throw std::invalid_argument("drive value overflows pin width: " + pin.name);
            }
            if (pin.waveform.kind == DriveWaveformKind::RZZ) {
                throw std::invalid_argument("explicit drive does not support an RZZ pin: " + pin.name);
            }
            if (pin.waveform.kind == DriveWaveformKind::RZ) {
                row_phase_(row_start, config_.timing.rz.edge_1, config_.timing.rz.base, "RZ edge_1");
                row_phase_(row_start, config_.timing.rz.edge_2, config_.timing.rz.base, "RZ edge_2");
            }
            driven_mask |= mask;
            break;
        }
        case VectorRow::ActionKind::Pulse: {
            const auto& pin = input_pin_(action.pin_name);
            if (pin.width != 1) {
                throw std::invalid_argument("pulse requires a single-bit input pin: " + pin.name);
            }
            if (pin.waveform.kind != DriveWaveformKind::RZ) {
                throw std::invalid_argument("pulse requires an RZ input pin: " + pin.name);
            }
            row_phase_(row_start, config_.timing.rz.edge_1, config_.timing.rz.base, "RZ edge_1");
            row_phase_(row_start, config_.timing.rz.edge_2, config_.timing.rz.base, "RZ edge_2");
            const uint32_t mask = 1U << pin.lsb;
            if ((driven_mask & mask) != 0U) {
                throw std::invalid_argument("input pin driven more than once in one row: " + pin.name);
            }
            driven_mask |= mask;
            break;
        }
        case VectorRow::ActionKind::Sample: {
            const auto& pin = output_pin_(action.pin_name);
            const uint32_t mask = value_mask(pin.width) << pin.lsb;
            if ((sampled_mask & mask) != 0U) {
                throw std::invalid_argument("output pin sampled more than once in one row: " + pin.name);
            }
            if ((action.value & ~value_mask(pin.width)) != 0U) {
                throw std::invalid_argument("sample value overflows pin width: " + pin.name);
            }
            row_phase_(row_start, config_.timing.stb.edge, config_.timing.stb.base, "STB edge");
            sampled_mask |= mask;
            break;
        }
        case VectorRow::ActionKind::Alert:
            break;
        }
    }

    ate_.begin_vector_row();
    for (const auto& action : row.actions_) {
        switch (action.kind) {
        case VectorRow::ActionKind::Drive: {
            const auto& pin = input_pin_(action.pin_name);
            if (pin.waveform.kind == DriveWaveformKind::RZ) {
                ate_.schedule_input_field_at(
                    row_phase_(row_start, config_.timing.rz.edge_1, config_.timing.rz.base, "RZ edge_1"),
                    pin.lsb, pin.width, action.value, action.pin_delay);
                ate_.schedule_input_field_at(
                    row_phase_(row_start, config_.timing.rz.edge_2, config_.timing.rz.base, "RZ edge_2"),
                    pin.lsb, pin.width, pin.default_value, action.pin_delay);
            } else {
                ate_.set_input_field(pin.lsb, pin.width, action.value, action.pin_delay);
            }
            break;
        }
        case VectorRow::ActionKind::Pulse: {
            const auto& pin = input_pin_(action.pin_name);
            const uint32_t active = (pin.default_value & 1U) == 0U ? 1U : 0U;
            ate_.schedule_input_pin_at(
                row_phase_(row_start, config_.timing.rz.edge_1, config_.timing.rz.base, "RZ edge_1"),
                pin.lsb, active != 0U, action.pin_delay);
            ate_.schedule_input_pin_at(
                row_phase_(row_start, config_.timing.rz.edge_2, config_.timing.rz.base, "RZ edge_2"),
                pin.lsb, pin.default_value != 0U, action.pin_delay);
            break;
        }
        case VectorRow::ActionKind::Sample: {
            const auto& pin = output_pin_(action.pin_name);
            ate_.expect_output_field(pin.lsb, pin.width, action.value, action.pin_delay);
            break;
        }
        case VectorRow::ActionKind::Alert:
            ate_.schedule_alert_at(row_start);
            break;
        }
    }

    ate_.commit_vector_row();
}

void AteBench::run(const AteEvent& event) {
    event.execute(*this);
}

void AteBench::idle(uint32_t rows) {
    for (uint32_t row = 0; row < rows; ++row) {
        run(VectorRow{});
    }
}

void AteBench::advance_phases(uint64_t count) {
    for (uint64_t phase = 0; phase < count; ++phase) {
        ate_.advance_phase();
    }
}

void AteBench::set_power_uv(const std::string& name, uint32_t uv) {
    if (name != "VDDQ" && name != "VDD") {
        throw std::invalid_argument("unknown POWER rail: " + name);
    }
    config_.power_uv[name == "VDD" ? "VDDQ" : name] = uv;
    ate_.set_dut_vddq_uv(uv);
}

void AteBench::set_dut_skew(const DutSkewConfig& config) {
    config_.skew = config;
    ate_.set_dut_skew(config);
}

uint64_t AteBench::wait(const std::string& pin_name, uint64_t max_rows) {
    const auto& pin = output_pin_(pin_name);
    const uint32_t initial_value = output_value_(pin);

    for (uint64_t rows = 1;; ++rows) {
        idle(1);
        if (output_value_(pin) != initial_value) {
            return rows;
        }
        if (max_rows != 0 && rows >= max_rows) {
            throw std::runtime_error(
                "wait timed out before output pin changed: " + pin_name);
        }
    }
}

AteBench::WaitResult AteBench::wait(const std::string& pin_name,
                                    uint64_t max_rows,
                                    const AteEvent& on_change) {
    return wait_with_handler_(pin_name, max_rows, on_change, WaitMode::Change);
}

AteBench::WaitResult AteBench::wait_rising(const std::string& pin_name,
                                           uint64_t max_rows,
                                           const AteEvent& on_rising) {
    return wait_with_handler_(pin_name, max_rows, on_rising, WaitMode::Rising);
}

AteBench::WaitResult AteBench::wait_falling(const std::string& pin_name,
                                            uint64_t max_rows,
                                            const AteEvent& on_falling) {
    return wait_with_handler_(pin_name, max_rows, on_falling, WaitMode::Falling);
}

AteBench::WaitResult AteBench::wait_with_handler_(const std::string& pin_name,
                                                  uint64_t max_rows,
                                                  const AteEvent& handler,
                                                  WaitMode mode) {
    if (wait_handler_active_) {
        throw std::runtime_error("nested wait event handlers are not supported");
    }

    const auto& pin = output_pin_(pin_name);
    uint32_t previous_value = output_value_(pin);

    for (uint64_t rows = 1;; ++rows) {
        idle(1);
        const uint32_t current_value = output_value_(pin);
        bool triggered = false;
        switch (mode) {
        case WaitMode::Change:
            triggered = current_value != previous_value;
            break;
        case WaitMode::Rising:
            triggered = previous_value == 0U && current_value != 0U;
            break;
        case WaitMode::Falling:
            triggered = previous_value != 0U && current_value == 0U;
            break;
        }

        if (triggered) {
            WaitResult result{
                .waited_rows = rows,
                .old_value = previous_value,
                .new_value = current_value,
                .handler_ran = true,
            };

            wait_handler_active_ = true;
            try {
                handler.execute(*this);
            } catch (...) {
                wait_handler_active_ = false;
                throw;
            }
            wait_handler_active_ = false;
            return result;
        }

        previous_value = current_value;
        if (max_rows != 0 && rows >= max_rows) {
            const std::string event_name = handler.name().empty() ? "<unnamed>" : handler.name();
            throw std::runtime_error(
                "wait timed out before output pin triggered event '" + event_name +
                "': " + pin_name);
        }
    }
}

bool AteBench::compare_all() {
    return ate_.compare_all();
}

uint32_t AteBench::output_value_(const OutputPinDef& pin) const {
    return (ate_.current_output_raw() >> pin.lsb) & value_mask(pin.width);
}

std::vector<uint32_t> AteBench::input_voltage(const std::string& pin_name) const {
    const auto& pin = input_pin_(pin_name);
    std::vector<uint32_t> values;
    values.reserve(pin.width);
    for (int offset = 0; offset < pin.width; ++offset) {
        values.push_back(ate_.current_input_voltage_uv(pin.lsb + offset));
    }
    return values;
}

std::vector<uint32_t> AteBench::ate_input_voltage(const std::string& pin_name) const {
    const auto& pin = input_pin_(pin_name);
    std::vector<uint32_t> values;
    values.reserve(pin.width);
    for (int offset = 0; offset < pin.width; ++offset) {
        values.push_back(ate_.current_ate_input_voltage_uv(pin.lsb + offset));
    }
    return values;
}

std::vector<uint32_t> AteBench::output_voltage(const std::string& pin_name) const {
    const auto& pin = output_pin_(pin_name);
    std::vector<uint32_t> values;
    values.reserve(pin.width);
    for (int offset = 0; offset < pin.width; ++offset) {
        values.push_back(ate_.current_output_voltage_uv(pin.lsb + offset));
    }
    return values;
}

const std::vector<SampleRecord>& AteBench::sample_records() const {
    return ate_.captured_samples();
}

bool AteBench::all_pass() {
    ate_.clear_compare_results();
    return ate_.compare_all();
}

void AteBench::print_samples() const {
    ate_.print_sample_records();
}
