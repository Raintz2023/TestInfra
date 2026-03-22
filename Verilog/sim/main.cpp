#include "VSocket.h"
#include "verilated.h"
#include "verilated_vcd_c.h"
#include <iostream>

vluint64_t sim_time = 0;

void tick(VSocket* top, VerilatedVcdC* tfp){
    // Clock control
    top->CLK = 0;
    top->eval();
    if (tfp) {
        tfp->dump(sim_time++);
    }

    top->CLK = 1;
    top->eval();
    if (tfp) {
        tfp->dump(sim_time++);
    }
}


int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);

    // ⭐ 必须开启 trace
    Verilated::traceEverOn(true);

    // ⭐ new DUT
    VSocket* top = new VSocket;

    // ⭐ new 波形对象
    VerilatedVcdC* tfp = new VerilatedVcdC;

    // ⭐ 绑定 trace
    top->trace(tfp, 99);

    // ⭐ 打开文件
    tfp->open("wave.vcd");

    // cycle 0：发脉冲
    top->DRIV = 1;
    top->DRIV_IN = 1;

    tick(top, tfp);
    tick(top, tfp);

    // cycle 1：拉低
    top->DRIV = 0;

    tick(top, tfp);
    tick(top, tfp);

    // reset 5 cycles
    for (int i = 0; i < 10; i++) {
        tick(top, tfp);
    }

    top->RST_N = 1;

    std::cout << "RESET DONE\n";

    top->DRIV = 0b1111111111111111;        
    top->DRIV_IN = 0b1111111111111111;
    top->DRIV_OFFSET = 0xFEDCBA9876543210;

    tick(top, tfp);

    top->DRIV = 0;

    top->SAMP = 0b1111;
    top->SAMP_OFFSET = 0x0000;

    for (int i = 0; i < 40; i++) {
        tick(top, tfp);
        std::cout << "Cycle " << i
                  << " SAMP_OUT=" << (int)top->SAMP_OUT
                  << std::endl;
    }

    // ⭐ 必须执行 final (Verilator 规范)
    top->final();

    // ⭐ 必须关闭波形文件，才能将缓冲区的数据写进磁盘
    if (tfp) {
        tfp->close();
        delete tfp;
    }
    // 释放 DUT
    delete top;
    
    return 0;
}