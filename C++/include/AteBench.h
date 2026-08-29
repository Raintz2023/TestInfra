#pragma once

#include "Ate.h"

#include <cstdint>
#include <optional>
#include <string>
#include <unordered_map>
#include <variant>
#include <vector>

struct InputPinDef {
    std::string name;
    int lsb = 0;
    int width = 1;
    DriveWaveform waveform = DriveWaveform::nrz();
    uint32_t default_value = 0;
    std::optional<AteInputVoltageConfig> ate_voltage;
};

struct OutputPinDef {
    std::string name;
    int lsb = 0;
    int width = 1;
    std::optional<AteOutputVoltageConfig> ate_voltage;
};

struct DutInputInterfaceDef {
    std::string pin_name;
    DutInputInterfaceConfig config;
};

struct DutOutputInterfaceDef {
    std::string pin_name;
    DutOutputInterfaceConfig config;
};

struct DutInterfaceDef {
    std::vector<DutInputInterfaceDef> inputs;
    std::vector<DutOutputInterfaceDef> outputs;
};

struct AteBenchConfig {
    std::string wave_path;
    bool trace_enable = true;
    TimingSet timing{};
    std::vector<InputPinDef> inputs;
    std::vector<OutputPinDef> outputs;
    DutInterfaceDef dut_interface;
    std::unordered_map<std::string, uint32_t> power_uv;
    DutSkewConfig skew;
};

class VectorRow {
public:
    VectorRow& drive(std::string pin_name, uint32_t value, uint32_t pin_delay = 0);
    VectorRow& pulse(std::string pin_name, uint32_t pin_delay = 0);
    VectorRow& sample(std::string pin_name, uint32_t expected, uint32_t pin_delay = 0);
    VectorRow& alert();

private:
    friend class AteBench;

    enum class ActionKind {
        Drive,
        Pulse,
        Sample,
        Alert,
    };

    struct Action {
        ActionKind kind = ActionKind::Drive;
        std::string pin_name;
        uint32_t value = 0;
        uint32_t pin_delay = 0;
    };

    std::vector<Action> actions_;
};

class AteBench;

class AteEvent {
public:
    explicit AteEvent(std::string name = {});

    AteEvent& run(VectorRow row);
    AteEvent& idle(uint32_t rows = 1);
    AteEvent& advance_phases(uint64_t phases);

    void execute(AteBench& bench) const;
    const std::string& name() const { return name_; }

private:
    struct RunStep {
        VectorRow row;
    };
    struct IdleStep {
        uint32_t rows = 1;
    };
    struct AdvanceStep {
        uint64_t phases = 0;
    };

    std::string name_;
    std::vector<std::variant<RunStep, IdleStep, AdvanceStep>> steps_;
};

class AteBench {
public:
    struct WaitResult {
        uint64_t waited_rows = 0;
        uint32_t old_value = 0;
        uint32_t new_value = 0;
        bool handler_ran = false;
    };

    explicit AteBench(AteBenchConfig config);

    void run(const VectorRow& row);
    void run(const AteEvent& event);
    void idle(uint32_t rows = 1);
    void advance_phases(uint64_t count);
    void set_power_uv(const std::string& name, uint32_t uv);
    void set_dut_skew(const DutSkewConfig& config);
    uint64_t wait(const std::string& pin_name, uint64_t max_rows = 0);
    WaitResult wait(const std::string& pin_name, uint64_t max_rows, const AteEvent& on_change);
    WaitResult wait_rising(const std::string& pin_name, uint64_t max_rows, const AteEvent& on_rising);
    WaitResult wait_falling(const std::string& pin_name, uint64_t max_rows, const AteEvent& on_falling);
    bool compare_all();

    std::vector<uint32_t> input_voltage(const std::string& pin_name) const;
    std::vector<uint32_t> ate_input_voltage(const std::string& pin_name) const;
    std::vector<uint32_t> output_voltage(const std::string& pin_name) const;
    const std::vector<SampleRecord>& sample_records() const;
    bool all_pass();
    void print_samples() const;

    ATE& engine() { return ate_; }
    const ATE& engine() const { return ate_; }

private:
    const InputPinDef& input_pin_(const std::string& name) const;
    const OutputPinDef& output_pin_(const std::string& name) const;
    uint32_t output_value_(const OutputPinDef& pin) const;
    uint64_t row_phase_(uint64_t row_start, uint64_t edge, int64_t base, const char* label) const;
    void validate_config_() const;
    void configure_engine_();
    enum class WaitMode {
        Change,
        Rising,
        Falling,
    };
    WaitResult wait_with_handler_(const std::string& pin_name,
                                  uint64_t max_rows,
                                  const AteEvent& handler,
                                  WaitMode mode);

    AteBenchConfig config_;
    ATE ate_;
    std::unordered_map<std::string, std::size_t> input_by_name_;
    std::unordered_map<std::string, std::size_t> output_by_name_;
    bool wait_handler_active_ = false;
};
