#include "Waveform.h"

DriveWaveform DriveWaveform::nrz(bool default_value) {
    DriveWaveform waveform;
    waveform.kind = DriveWaveformKind::NRZ;
    waveform.default_value = default_value;
    return waveform;
}

DriveWaveform DriveWaveform::rzz(bool default_value) {
    DriveWaveform waveform;
    waveform.kind = DriveWaveformKind::RZZ;
    waveform.default_value = default_value;
    return waveform;
}
