#include "Pattern.h"

#include <cstddef>
#include <stdexcept>
#include <utility>

SocSchema::SocSchema(std::vector<SocPin> pins) : pins_(std::move(pins)) {
    for (const auto& pin : pins_) {
        by_name_[pin.name] = pin;
    }
}

void SocSchema::configure(ATE& ate) const {
    ate.clear_input_pin_configs();
    ate.clear_output_pin_configs();
    for (const auto& pin : pins_) {
        if (pin.input) {
            ate.configure_input_pin(pin.lsb, pin.width, pin.waveform, pin.default_value);
        } else {
            ate.configure_output_pin(pin.lsb, pin.width, pin.default_value);
        }
    }
}

const SocPin& SocSchema::pin(const std::string& name) const {
    auto it = by_name_.find(name);
    if (it == by_name_.end()) {
        throw std::runtime_error("unknown SOC pin: " + name);
    }
    return it->second;
}

CommandSet::CommandSet(std::vector<CommandDef> defs) {
    for (auto& def : defs) {
        by_name_[def.name] = std::move(def);
    }
}

const CommandDef& CommandSet::command(const std::string& name) const {
    auto it = by_name_.find(name);
    if (it == by_name_.end()) {
        throw std::runtime_error("unknown command: " + name);
    }
    return it->second;
}

void apply_command(ATE& ate,
                   const SocSchema& schema,
                   const CommandDef& command,
                   const std::vector<uint32_t>& values) {
    std::size_t value_idx = 0;
    ate.begin_vector_row();

    for (const auto& role : command.roles) {
        const auto& pin = schema.pin(role.pin_name);
        if (!pin.input) {
            throw std::runtime_error("apply command role is not an input pin: " + role.pin_name);
        }
        if (role.needs_value) {
            if (value_idx >= values.size()) {
                throw std::runtime_error("command value missing for pin: " + role.pin_name);
            }
            ate.set_input_field(pin.lsb, pin.width, values[value_idx]);
            ++value_idx;
        } else {
            ate.activate_input_pin(pin.lsb);
        }
    }

    if (value_idx != values.size()) {
        throw std::runtime_error("too many command values");
    }

    ate.commit_vector_row();
}

void expect_command(ATE& ate,
                    const SocSchema& schema,
                    const CommandDef& command,
                    const std::vector<uint32_t>& values) {
    std::size_t value_idx = 0;
    for (const auto& role : command.roles) {
        const auto& pin = schema.pin(role.pin_name);
        if (pin.input) {
            throw std::runtime_error("expect command role is not an output pin: " + role.pin_name);
        }
        if (!role.needs_value) {
            throw std::runtime_error("expect command role needs an expected value: " + role.pin_name);
        }
        if (value_idx >= values.size()) {
            throw std::runtime_error("expected value missing for pin: " + role.pin_name);
        }
        ate.expect_output_field(pin.lsb, pin.width, values[value_idx]);
        ++value_idx;
    }

    if (value_idx != values.size()) {
        throw std::runtime_error("too many expected values");
    }
}
