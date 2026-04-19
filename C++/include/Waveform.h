#pragma once

enum class DriveWaveformKind {
    NRZ,
    RZZ
};

struct DriveWaveform {
    DriveWaveformKind kind = DriveWaveformKind::NRZ;
    bool default_value = false;

    static DriveWaveform nrz(bool default_value = false);
    static DriveWaveform rzz(bool default_value = false);
};
