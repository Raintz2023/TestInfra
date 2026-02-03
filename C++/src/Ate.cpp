#include "Ate.h"

// RAII: 资源获取即初始化，谁获取、使用资源，谁就应该初始化时获取资源，销毁时负责释放资源。
// 不要将不安全对象对外暴露，以免外部将其释放。
ATE::ATE(std::string wave_name, bool trace_enable, uint8_t top_data_init) 
    : contextp_(std::make_unique<VerilatedContext>()), clock_(0), top_data_(top_data_init) {
    
    this->contextp_->traceEverOn(trace_enable);
    this->atep_ = std::make_unique<VAte>(this->contextp_.get());

    if (trace_enable && !wave_name.empty()) {
        this->tfp_ = std::make_unique<VerilatedVcdC>();
        this->atep_->trace(this->tfp_.get(), 99);
        this->tfp_->open(wave_name.c_str());
    }

    // ========= 初始化引脚 =========
    this->atep_->CLK   = 0;
    this->atep_->RST_N = 0;
    this->atep_->R     = 0;
    this->atep_->W     = 0;
    this->atep_->ADDR  = 0;
    this->atep_->DQ_IN = 0;

    // ========= 复位序列 =========
    this->init_reset_sequence_();
}

ATE::~ATE() {
    // 析构顺序和构造顺序相反
    if (this->tfp_) {
        this->tfp_->close();
    }
    if (this->atep_) {
        this->atep_->final();
    }
}

void ATE::init_reset_sequence_() {
    // 复位保持 2 个周期
    this->tick();
    this->tick();

    // 释放复位
    this->atep_->RST_N = 1;
    this->tick();

    this->sample_cnts_ = 0;
    this->top_data_vec_.clear();
}

void ATE::tick(){
    // 时钟控制函数
    // negedge
    this->atep_->CLK = 0;
    this->atep_->eval();
    this->tfp_->dump(this->clock_++);

    // posedge
    this->atep_->CLK = 1;
    this->atep_->eval();
    this->tfp_->dump(this->clock_++);
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
    // 在 posedge 到来前准备好写信号
    this->atep_->R = 0;
    this->atep_->W = 1;

    this->atep_->ADDR = addr & 0xFF;

    // this->atep_->DQ_IN = this->top_data_;

    // 跑一个周期：posedge 时写入
    this->tick();

    // 写完立刻撤销 W
    this->atep_->W = 0;
    this->tick();

}

void ATE::read(uint64_t addr) {
    this->atep_->W = 0;
    this->atep_->R = 1;
    this->atep_->DQ_IN = 0;

    this->atep_->ADDR = addr & 0xFF;

    // 读请求
    this->tick();
    // 读完撤销 R
    this->atep_->R = 0;
    this->tick();
}

void ATE::drive(unsigned int offset) {

    if (offset > 0) {
        this->atep_->DRIV_SHIFT = 1;
        this->atep_->DRIV_FRONT = offset;
    }
    else {
        this->atep_->DRIV_SHIFT = 0;
    }

    this->atep_->DQ_IN = this->top_data_;

    this->atep_->DRIV = 1;
    this->tick();

    this->atep_->DRIV = 0;
    this->tick();
}


void ATE::sample(int offset) {

    this->sample_cnts_ += 1;
    this->top_data_vec_.push_back(this->top_data_);

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

    // for (int i = 0; i < this->sample_cnts_; i++) {
    //     std::cout << "Sample data:" << (uint32_t)this->atep_->OUT_REG[i] << std::endl;
    //     std::cout << "Top data:" << (uint32_t)this->top_data_vec_[i] << std::endl;
    // }
    if (sample_cnts == strb_cnts) {
        bool pass = true;
        for (int i = 0; i < this->sample_cnts_; i++) {
            if ((uint32_t)this->top_data_vec_[i] != (uint32_t)this->atep_->OUT_REG[i]) {
                pass = false;
                break;
            }
        }
        if (pass) {
            printf("*");
        }
        else {
            printf(".");
        }
    }
    else {
        printf(".");
    }
}

void ATE::reverse_top_data() {
    this->top_data_ = this->top_data_ ^ 0xFF;
}

void ATE::set_top_data(uint8_t data) {
    this->top_data_ = data & 0xFF;
}


#ifdef ATE_PYBIND
    namespace py = pybind11;

    PYBIND11_MODULE(ate, m) {
        m.doc() = "pybind11 ate class";

        py::class_<ATE>(m, "ATE")
            .def(py::init<std::string, bool, uint8_t>(), py::arg("wave_name"), py::arg("trave_enable"), py::arg("top_data_init"))
            .def("tick", &ATE::tick)
            .def("write", &ATE::write, py::arg("addr"))
            .def("mr_write", &ATE::mr_write, py::arg("addr"), py::arg("mr_data"))
            .def("read", &ATE::read, py::arg("addr"))
            .def("sample", &ATE::sample, py::arg("offset"))
            .def("compare", &ATE::compare)
            .def("reverse_top_data", &ATE::reverse_top_data)
            .def("top_data", &ATE::top_data)
            .def("set_top_data", &ATE::set_top_data, py::arg("data"))
            .def("clock", &ATE::clock)
            .def("print", &ATE::print);
    }
#endif