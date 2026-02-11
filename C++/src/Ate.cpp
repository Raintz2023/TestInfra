#include "Ate.h"

// RAII: Resource acquisition is initialization. 
// What acquires and uses a resource should be responsible for obtaining it during construction and releasing it upon destruction.
// Do not expose unsafe objects to the outside, as doing so may cause them to be released by the external party.
ATE::ATE(std::string wave_name, bool trace_enable, uint8_t top_data_init) 
    : contextp_(std::make_unique<VerilatedContext>()), clock_(0), top_data_(top_data_init) {
    
    this->contextp_->traceEverOn(trace_enable);
    this->atep_ = std::make_unique<VAte>(this->contextp_.get());

    if (trace_enable && !wave_name.empty()) {
        this->tfp_ = std::make_unique<VerilatedVcdC>();
        this->atep_->trace(this->tfp_.get(), 99);
        this->tfp_->open(wave_name.c_str());
    }

    // ========= Initialize the pins =========
    this->atep_->CLK   = 0;
    this->atep_->RST_N = 0;
    this->atep_->R     = 0;
    this->atep_->W     = 0;
    this->atep_->ADDR  = 0;
    this->atep_->DQ_IN = 0;

    // ========= Reset sequence =========
    this->init_reset_sequence_();
}

ATE::~ATE() {
    // The order of destruction is opposite to the order of construction.
    if (this->tfp_) {
        this->tfp_->close();
    }
    if (this->atep_) {
        this->atep_->final();
    }
}

void ATE::init_reset_sequence_() {
    this->tick();
    this->tick();

    this->atep_->RST_N = 1;
    this->tick();

    this->sample_cnts_ = 0;
    this->top_data_vec_.clear();
}

void ATE::tick(){
    // Clock control
    this->atep_->CLK = 0;
    this->atep_->eval();
    if (this->tfp_) {
        this->tfp_->dump(this->clock_++);
    }

    this->atep_->CLK = 1;
    this->atep_->eval();
    if (this->tfp_) {
        this->tfp_->dump(this->clock_++);
    }
}

void ATE::mr_write(uint64_t addr, uint64_t mr_data) {
    this->atep_->MRR = 0;
    this->atep_->MRW = 1;

    this->atep_->ADDR = addr & 0xFF;

    this->atep_->MR_IN = mr_data;

    this->tick();
    
    this->atep_->MRW = 0;
    this->tick();
}

void ATE::mr_read(uint64_t addr) {
    this->atep_->MRR = 1;
    this->atep_->MRW = 0;

    this->atep_->ADDR = addr & 0xFF;

    this->tick();
    
    this->atep_->MRW = 0;
    this->tick();
}

void ATE::write(uint64_t addr) {
    this->atep_->R = 0;
    // tick 1
    this->atep_->W = 1;
    this->atep_->ADDR = addr & 0xFF;
    this->tick();
    this->atep_->W = 0;
    this->tick();
    // tick 2
    this->atep_->W = 1;
    this->atep_->ADDR = (addr + 1) & 0xFF;
    this->tick();
    this->atep_->W = 0;
    this->tick();
    // tick 3
    this->atep_->W = 1;
    this->atep_->ADDR = (addr + 2) & 0xFF;
    this->tick();
    this->atep_->W = 0;
    this->tick();
    // tick 4
    this->atep_->W = 1;
    this->atep_->ADDR = (addr + 3) & 0xFF;
    this->tick();
    this->atep_->W = 0;
    this->tick();
}

void ATE::read(uint64_t addr) {
    this->atep_->W = 0;
    this->atep_->DQ_IN = 0;

    // tick 1
    this->atep_->R = 1;
    this->atep_->ADDR = addr & 0xFF;
    this->tick();
    this->atep_->R = 0;
    this->tick();
    // tick 2
    this->atep_->R = 1;
    this->atep_->ADDR = (addr + 1) & 0xFF;
    this->tick();
    this->atep_->R = 0;
    this->tick();
    // tick 3
    this->atep_->R = 1;
    this->atep_->ADDR = (addr + 2) & 0xFF;
    this->tick();
    this->atep_->R = 0;
    this->tick();
    // tick 4
    this->atep_->R = 1;
    this->atep_->ADDR = (addr + 3) & 0xFF;
    this->tick();
    this->atep_->R = 0;
    this->tick();
}

void ATE::drive(unsigned int offset, bool inverted) {

    uint8_t top_data = (inverted)? this->top_data_ ^ 0xFF : this->top_data_;

    if (offset > 0) {
        this->atep_->DRIV_SHIFT = 1;
        this->atep_->DRIV_FRONT = offset;
    }
    else {
        this->atep_->DRIV_SHIFT = 0;
    }

    this->atep_->DQ_IN = top_data;

    this->atep_->DRIV = 1;
    this->tick();

    this->atep_->DRIV = 0;
    this->tick();
}


void ATE::sample(int offset, bool inverted) {

    uint8_t top_data = (inverted)? this->top_data_ ^ 0xFF : this->top_data_;

    this->sample_cnts_ += 1;
    this->top_data_vec_.push_back(top_data);

    if (offset > 0) {
        this->atep_->STRB_SHIFT = 1;
        this->atep_->STRB_FRONT = abs(offset);
    }
    else {
        this->atep_->STRB_SHIFT = 0;
        this->atep_->STRB_BACK = abs(offset);
    }

    this->atep_->STRB = 1;
    this->tick();

    this->atep_->STRB = 0;
    this->tick();
}

void ATE::compare() {
    uint32_t sample_cnts = this->sample_cnts_;
    uint32_t strb_cnts = (uint32_t)this->atep_->STRB_CNTS;

    if (sample_cnts == strb_cnts) {
        bool pass = true;
        for (int i = 0; i < this->sample_cnts_; i++) {
            if ((uint32_t)this->top_data_vec_[i] != (uint32_t)this->atep_->OUT_REG[i]) {
                pass = false;
                break;
            }
        }
        if (pass) {
            std::cout << "*" << std::flush;
        }
        else {
            std::cout << "." << std::flush;
        }
    }
    else {
        std::cout << "." << std::flush;
    }
}

void ATE::set_top_data(uint8_t data) {
    this->top_data_ = data & 0xFF;
}


#ifdef ATE_PYBIND
    namespace py = pybind11;

    PYBIND11_MODULE(ate, m) {
        m.doc() = "pybind11 ate class";

        py::class_<ATE>(m, "ATE")
            .def(py::init<std::string, bool, uint8_t>(), py::arg("wave_name"), py::arg("trace_enable"), py::arg("top_data_init"))
            .def("tick", &ATE::tick)
            .def("write", &ATE::write, py::arg("addr"))
            .def("mr_write", &ATE::mr_write, py::arg("addr"), py::arg("mr_data"))
            .def("mr_read", &ATE::mr_read, py::arg("addr"))
            .def("read", &ATE::read, py::arg("addr"))
            .def("drive", &ATE::drive, py::arg("offset"), py::arg("inverted"))
            .def("sample", &ATE::sample, py::arg("offset"), py::arg("inverted"))
            .def("compare", &ATE::compare)
            .def("top_data", &ATE::top_data)
            .def("set_top_data", &ATE::set_top_data, py::arg("data"))
            .def("clock", &ATE::clock);
    }
#endif