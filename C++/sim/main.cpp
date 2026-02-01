#include "Ate.h"

int main(int argc, char** argv) {

    // for (int y = -10; y <= 10; y++) {
    //     for (int x = 0; x <= 50; x++) {
    //         auto wave_name = std::format("/root/Code/TestInfra/Verilog/wave/wave_{}_{}.vcd", x, y);

    //         uint8_t top_data = 0xFF;

    //         ATE ate{wave_name, true, top_data};

    //         ate.mr_write(0, 56);
    //         ate.mr_write(1, 40);

    //         uint64_t addr = 0;
    //         ate.write(addr);

    //         for (int j = 0; j < x; j++) {
    //             ate.tick();
    //         }

    //         ate.read(addr);

    //         for (int j = 0; j < 50; j++) {
    //             ate.tick();
    //         }
    //         ate.sample(y);

    //         for (int j = 0; j < 50; j++) {
    //             ate.tick();
    //         }

    //         ate.compare();
    //         // addr += 1;
    //         // ate.reverse_top_data();
    //         // ate.write(addr);
    //         // addr += 1;
    //         // ate.reverse_top_data();
    //         // ate.write(addr);
    //         // addr += 1;
    //         // ate.reverse_top_data();
    //         // ate.write(addr);
    //         // addr += 1;
    //         // ate.reverse_top_data();
    //         // addr = 0;
    //         // ate.read(addr);
    //         // addr += 1;
    //         // //ate.tick();
    //         // ate.read(addr);
    //         // addr += 1;
    //         // //ate.tick();
    //         // ate.read(addr);
    //         // addr += 1;
    //         // //ate.tick();
    //         // ate.read(addr);
    //         // addr += 1;
    //         // for (int j = 0; j < 50; j++) {
    //         //     ate.tick();
    //         // }
    //         // ate.sample(i);
    //         // ate.tick();
    //         // ate.reverse_top_data();
    //         // ate.sample(i);
    //         // ate.tick();
    //         // ate.reverse_top_data();
    //         // ate.sample(i);
    //         // ate.tick();
    //         // ate.reverse_top_data();
    //         // ate.sample(i);
    //         // ate.tick();
    //         // for (int j = 0; j < 40; j++) {
    //         //     ate.tick();
    //         // }
    //         // ate.compare();
    //     }
    //     printf("\n");
    // }
    // printf("\n");

    for (int y = -10; y <= 10; y++) {
        auto wave_name = std::format("/root/Code/TestInfra/Verilog/wave/wave_{}.vcd", y);

        uint8_t top_data = 0xFF;

        ATE ate{wave_name, true, top_data};

        ate.mr_write(0, 56);
        ate.mr_write(1, 40);

        uint64_t addr = 0;
        ate.write(addr);

        for (int j = 0; j < 35; j++) {
            ate.tick();
        }
        ate.drive();
        ate.drive();
        ate.drive();
        ate.drive();

        ate.read(addr);

        for (int j = 0; j < 50; j++) {
            ate.tick();
        }
        ate.sample(y);

        for (int j = 0; j < 50; j++) {
            ate.tick();
        }

        ate.compare();


    }
    printf("\n");
    return 0;
}