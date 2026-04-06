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

    socketp_->CLK = 0;
    socketp_->RST_N = 0;
    clear_driv_();
    clear_samp_();

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
    tick();
    tick();

    socketp_->RST_N = 0;
    for (int i = 0; i < 8; ++i) {
        tick();
    }

    socketp_->RST_N = 1;
    tick();
    tick();

    clear_captured_samples();
    clear_compare_results();
    pending_compare_specs_.clear();
    cycle_ = 0;
}

// Public reset entry. Wrapper code can call this to restart a test sequence.
void ATE::reset() {
    socketp_->RST_N = 0;
    clear_driv_();
    clear_samp_();

    tick();
    tick();

    socketp_->RST_N = 1;
    tick();
    tick();

    clear_captured_samples();
    clear_compare_results();
    pending_compare_specs_.clear();
    cycle_ = 0;
}

// Public single-cycle advance. This is the base timing primitive for all custom flows.
void ATE::tick() {
    socketp_->CLK = 0;
    socketp_->eval();
    if (tfp_) {
        tfp_->dump(clock_++);
    }

    socketp_->CLK = 1;
    socketp_->eval();
    capture_sample_if_ready_();
    if (tfp_) {
        tfp_->dump(clock_++);
    }

    clear_driv_();
    clear_samp_();
    ++cycle_;
}

// Public convenience helper for advancing multiple cycles.
void ATE::run_cycles(uint32_t cycles) {
    for (uint32_t i = 0; i < cycles; ++i) {
        tick();
    }
}

// Public convenience helper: discard the currently staged drive operation.
void ATE::clear_drive() {
    clear_driv_();
}

// Public convenience helper: discard the currently staged sample operation.
void ATE::clear_sample() {
    clear_samp_();
}

// Public drive primitive for one input pin.
void ATE::stage_drive_pin(int pin, bool value, uint32_t delay) {
    validate_pin_index_(pin, kPinInCount, "drive pin");
    set_driv_pin_(pin, value, delay);
}

// Public drive primitive for a contiguous input field.
void ATE::stage_drive_field(int lsb, int width, uint32_t value, uint32_t delay) {
    validate_field_(lsb, width, kPinInCount, "drive field");
    set_driv_field_(lsb, width, value, delay);
}

// Public execute step for the staged drive request.
void ATE::pulse_drive() {
    pulse_driv_();
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
        enable_all_samples_(spec.delay);
        break;
    case CompareSpec::Mode::SinglePin:
        set_samp_pin_(spec.lsb, spec.delay);
        break;
    case CompareSpec::Mode::Field:
        set_samp_field_(spec.lsb, spec.width, spec.delay);
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
    tick();
    tick();
}

// Internal pulse wrapper. External code should prefer pulse_sample().
void ATE::pulse_samp_() {
    tick();
    tick();
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

    py::class_<ATE>(m, "ATE")
        .def(py::init<std::string, bool, uint32_t>(),
             py::arg("wave_name") = "",
             py::arg("trace_enable") = true,
             py::arg("top_data_init") = 0)
        .def("tick", &ATE::tick)
        .def("run_cycles", &ATE::run_cycles, py::arg("cycles"))
        .def("reset", &ATE::reset)
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
        .def("pulse_drive", &ATE::pulse_drive)
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
