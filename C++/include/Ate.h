#include "VAte.h"
#include "verilated.h"
#include "verilated_vcd_c.h"

#include <bitset>
#include <cstdint>
#include <string>
#include <format>
#include <iostream>
#include <memory>
#include <vector>


#ifdef ATE_PYBIND
    #include <pybind11/pybind11.h>
    #include <pybind11/stl.h>
#endif

class ATE {

public:

    // 显示构造：波形文件名 + 是否启用 trace + 初始 top_data
    explicit ATE(std::string wave_name = {},
                 bool trace_enable = true,
                 uint8_t top_data_init = 0xFF);

    ~ATE();

    void tick();

    void mr_write(uint64_t addr, uint64_t mr_data);

    void mr_read(uint64_t addr);

    void write(uint64_t addr);

    void read(uint64_t addr);

    void drive(unsigned int offset=0);

    void sample(int offset=0);

    void compare();

    void reverse_top_data();

    uint8_t top_data() const { return top_data_; }

    void set_top_data(uint8_t data=0x00);

    uint64_t clock() const { return clock_; }

    void print(std::string s) { std::cout << s << std::endl;}

private:

    void init_reset_sequence_();

    std::unique_ptr<VerilatedContext> contextp_;
    std::unique_ptr<VAte> atep_;
    std::unique_ptr<VerilatedVcdC> tfp_;

    uint64_t clock_ = 0;
    uint8_t top_data_ = 0xFF;

public:
    uint32_t sample_cnts_ = 0;
    std::vector<uint8_t> top_data_vec_;
};
