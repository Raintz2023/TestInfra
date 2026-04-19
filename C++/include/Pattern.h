#pragma once

#include "Ate.h"

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

struct SocPin {
    std::string name;
    bool input = true;
    int lsb = 0;
    int width = 1;
    DriveWaveform waveform = DriveWaveform::nrz();
    uint32_t default_value = 0;
};

struct CommandRole {
    std::string pin_name;
    bool needs_value = false;
};

struct CommandDef {
    std::string name;
    std::vector<CommandRole> roles;
};

class SocSchema {
public:
    explicit SocSchema(std::vector<SocPin> pins);

    void configure(ATE& ate) const;
    const SocPin& pin(const std::string& name) const;

private:
    std::vector<SocPin> pins_;
    std::unordered_map<std::string, SocPin> by_name_;
};

class CommandSet {
public:
    explicit CommandSet(std::vector<CommandDef> defs);

    const CommandDef& command(const std::string& name) const;

private:
    std::unordered_map<std::string, CommandDef> by_name_;
};

void apply_command(ATE& ate,
                   const SocSchema& schema,
                   const CommandDef& command,
                   const std::vector<uint32_t>& values);

void expect_command(ATE& ate,
                    const SocSchema& schema,
                    const CommandDef& command,
                    const std::vector<uint32_t>& values);
