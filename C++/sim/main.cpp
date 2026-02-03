#include "Ate.h"

int main(int argc, char** argv) {

    for (int y = -10; y <= 10; y++) {
        for (int x = 0; x <= 10; x++) {
            auto wave_name = std::format("/root/Code/TestInfra/Verilog/wave/wave_{}_{}.vcd", x, y);  

            uint8_t top_data = 0xFF;
            uint64_t addr = 0;

            ATE ate{wave_name, true, top_data};  // 不跟踪会报错，待解决 ************

            ate.mr_write(0, 56);
            ate.mr_write(1, 54);

            for (int j = 0; j < 10; j++) {
                ate.tick();
            }

            ate.write(addr);
            addr++;
            ate.write(addr);
            addr++;
            ate.write(addr);
            addr++;
            ate.write(addr);
            addr++;
            ate.write(addr);

            for (int j = 0; j < 40; j++) {
                ate.tick();
            }

            ate.drive(x);
            ate.reverse_top_data();
            ate.drive(x);
            ate.reverse_top_data();
            ate.drive(x);
            ate.reverse_top_data();
            ate.drive(x);
            ate.reverse_top_data();
            ate.drive(x);

            for (int j = 0; j < 10; j++) {
                ate.tick();
            }

            addr = 0;

            ate.read(addr);
            addr++;
            ate.read(addr);
            addr++;
            ate.read(addr);
            addr++;
            ate.read(addr);
            addr++;
            ate.read(addr);

            for (int j = 0; j < 50; j++) {
                ate.tick();
            }

            ate.sample(y);
            ate.reverse_top_data();
            ate.sample(y);
            ate.reverse_top_data();
            ate.sample(y);
            ate.reverse_top_data();
            ate.sample(y);
            ate.reverse_top_data();
            ate.sample(y);

            for (int j = 0; j < 50; j++) {
                ate.tick();
            }

            ate.compare();

            for (int j = 0; j < 10; j++) {
                ate.tick();
            }
        }
        printf("\n");
    }
    printf("\n");


    return 0;
}