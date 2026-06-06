#pragma once

enum class DriveWaveformKind {
    NRZ,
    RZ,
    RZZ
};

struct DriveWaveform {
    DriveWaveformKind kind = DriveWaveformKind::NRZ;
    bool default_value = false;

    static DriveWaveform nrz(bool default_value = false);
    static DriveWaveform rz(bool default_value = false);
    static DriveWaveform rzz(bool default_value = false);
};
